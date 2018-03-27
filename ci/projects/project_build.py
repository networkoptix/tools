# base project for CI and Release projects

import logging
import os.path
import os
import glob
import abc
import re
import yaml

from pony.orm import db_session

from junk_shop import (
    models,
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    BuildInfoLoader,
)
from utils import ensure_dir_missing
from project_nx_vms import BUILD_INFO_FILE, NxVmsProject
from command import (
    CleanDirCommand,
    PrepareVirtualEnvCommand,
    ArchiveArtifactsCommand,
    NodeCommand,
    ParallelJob,
    ParallelCommand,
    BooleanProjectParameter,
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
    UnstashCommand,
    SetBuildResultCommand,
)
from clean_stamps import CleanStamps
from diff_parser import load_hg_changes
from email_sender import EmailSender
from build_node_job import BUILD_INFO_STASH_NAME_FORMAT, BUILD_INFO_FILE_NAME_FORMAT, PlatformBuildInfo, BuildNodeJob
from webadmin import WEBADMIN_STASH_NAME, BuildWebAdminJob

log = logging.getLogger(__name__)


VERSION_FILE = 'version'
BUILD_INFO_FILE_NAME_GLOB = 'build_info*.yaml'  # build infos for platforms and for whole build
WEBADMIN_NODE = 'webadmin'
WEBADMIN_EXTERNAL_DIR = 'webadmin-external'
WEBADMIN_PLATFORM_NAME = 'webadmin'


class BuildProject(NxVmsProject):

    __metaclass__ = abc.ABCMeta

    def __init__(self, input_state, in_assist_mode):
        NxVmsProject.__init__(self, input_state, in_assist_mode)
        self._build_error_list = []
        self.clean_stamps = CleanStamps(self.state)

    # do all the stuff, or just update project projerties
    def must_actually_do_build(self):
        return self.params.action == 'build'

    @property
    def db_config(self):
        user, password = self.credentials.junk_shop_db.split(':')
        return DbConfig(self.config.junk_shop.db_host, user, password)

    @property
    def all_platform_list(self):
        return sorted(self.config.platforms.keys())

    @abc.abstractproperty
    def days_to_keep_old_builds(self):
        pass

    @abc.abstractproperty
    def enable_concurrent_builds(self):
        pass

    @abc.abstractproperty
    def requested_platform_list(self):
        pass

    # value for junk-shop model.Build property
    @abc.abstractproperty
    def customization(self):
        pass

    @abc.abstractproperty
    def requested_customization_list(self):
        pass

    @abc.abstractproperty
    def release(self):
        pass

    @abc.abstractproperty
    def cloud_group(self):
        pass

    @abc.abstractproperty
    def must_store_artifacts_in_different_customization_dirs(self):
        pass

    @property
    def add_qt_pdb_by_default(self):
        return False

    @property
    def checkout_nx_vms_revision(self):
        return None

    @property
    def custom_cmake_args(self):
        return ''

    @property
    def run_unit_tests_by_default(self):
        return True

    @property
    def deploy_webadmin_for_version(self):
        return False

    @property
    def project_name(self):
        if self.in_assist_mode:
            return 'assist-ci-%s' % self.jenkins_env.job_name
        else:
            return self.project_id

    @property
    def prepare_nx_vms_command_list(self):
        return self.make_prepare_nx_vms_command_list(self.checkout_nx_vms_revision)

    # init  ========================================================================================
    def stage_init(self):
        return self.initial_stash_nx_vms_command_list + self.prepare_nx_vms_command_list + [
            self.make_python_stage_command('set_properties'),
            ]


    # set_properties  ========================================================================================
    def stage_set_properties(self):
        command_list = [self._set_project_properties_command]
        if self.must_actually_do_build():
            command_list += [self.make_python_stage_command('prepare_for_build')]
        return command_list

    @property
    def _set_project_properties_command(self):
        return SetProjectPropertiesCommand(
            parameters=self.get_project_parameters(),
            enable_concurrent_builds=False,
            days_to_keep_old_builds=self.days_to_keep_old_builds,
            )

    def get_project_parameters(self):
        parameters = self.default_parameters + [
            ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                       ['build', 'update_properties']),
            BooleanProjectParameter('do_build', 'Do actual build', default_value=True),
            BooleanProjectParameter('build_webadmin', 'Build webadmin', default_value=True),
            BooleanProjectParameter('deploy_webadmin', 'Deploy webadmin (external.dat) to rdep', default_value=True),
            BooleanProjectParameter('run_unit_tests', 'Run unit tests', default_value=self.run_unit_tests_by_default),
            BooleanProjectParameter('clean_build', 'Build from scratch', default_value=False),
            BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
            BooleanProjectParameter('clean_only', 'Clean workspaces instead of build', default_value=False),
            BooleanProjectParameter('add_qt_pdb', 'Tell me if you know what this parameter means',
                                        default_value=self.add_qt_pdb_by_default),
            ]
        return parameters

    # Check if this build must be skipped. Called after nx_vms repo is inited/updated
    # For CI build is skipped if there are more commits to nx_vms repo.
    def must_skip_this_build(self):
        return False

    def is_hardware_signing_enabled(self, customization, platform):
        return False


    # prepare_for_build ============================================================================
    def stage_prepare_for_build(self):
        log.info('requested platform_list = %r', self.requested_platform_list)
        log.info('requested customization_list = %r', self.requested_customization_list)

        self.clean_stamps.init_master(self.params)
        if self.must_skip_this_build():
            return None
        self._cleanup_previous_build_info_files()
        self._init_build_info()

        return [
            self._make_webadmin_build_command(),
            self._make_platform_build_command(),
            ] + self._make_finalize_command_list()

    def _cleanup_previous_build_info_files(self):
        for fname in glob.glob(BUILD_INFO_FILE_NAME_GLOB):
            log.debug('Removing build info from previous build: %r', fname)
            os.remove(fname)

    # create models.Build and create models.BuildChangeSet records for it
    def _init_build_info(self):
        repository = self._create_junk_shop_repository()
        revision_info = update_build_info(repository, 'nx_vms')
        self.scm_info['nx_vms'].set_prev_revision(revision_info.prev_revision)  # will be needed later

    def _create_junk_shop_repository(self, platform=None):
        return DbCaptureRepository(self.db_config, self._make_build_parameters(self.customization, platform))

    # values for models.Build fields and models.Run roots
    def _make_build_parameters(self, customization, platform=None):
        nx_vms_scm_info = self.scm_info['nx_vms']
        is_incremental = not (self.params.clean or self.params.clean_build)
        return BuildParameters(
            project=self.project_name,
            branch=self.nx_vms_branch_name,
            build_num=self.jenkins_env.build_number,
            release=self.release,
            configuration='release',
            cloud_group=self.cloud_group,
            customization=customization,
            platform=platform,
            add_qt_pdb=self.params.add_qt_pdb or self.release == 'release',  # ENV-155 Always add qt pdb for releases
            is_incremental=is_incremental,
            jenkins_url=self.jenkins_env.build_url,
            repository_url=nx_vms_scm_info.repository_url,
            revision=nx_vms_scm_info.revision,
            )

    def _make_webadmin_build_command(self):
        workspace_dir = self._make_workspace_name('webadmin')
        job_command_list = self.prepare_devtools_command_list + self.prepare_nx_vms_command_list + [
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            self.make_python_stage_command('build_webadmin'),
            ]
        return NodeCommand(self._get_node_label(WEBADMIN_NODE), workspace_dir, job_command_list)

    def _make_platform_build_command(self):
        job_list = [self._make_parallel_job(platform) for platform in self.requested_platform_list]
        return ParallelCommand(job_list)

    def _make_finalize_command_list(self):
        if self.params.clean_only:
            return []
        return [
            CleanDirCommand('dist'),
            ] + list(self._unstash_results_command_list) + [
            self.make_python_stage_command('finalize'),
            ]

    def _make_parallel_job(self, platform):
        platform_config = self.config.platforms[platform]
        node = self._get_node_label(platform_config.build_node)
        job_command_list = []
        if self.params.clean or self.params.clean_only:
            job_command_list += [
                CleanDirCommand(),
                ]
        if not self.params.clean_only:
            job_command_list += self._make_node_stage_command_list(platform)
        job_name = platform
        workspace_dir = self._make_workspace_name(job_name)
        return ParallelJob(job_name, [NodeCommand(node, workspace_dir, job_command_list)])

    def _make_node_stage_command_list(self, platform, phase=1):
         return self.prepare_devtools_command_list + self.prepare_nx_vms_command_list + [
             CleanDirCommand(WEBADMIN_EXTERNAL_DIR),  # clean from previous builds
             UnstashCommand(WEBADMIN_STASH_NAME, dir=WEBADMIN_EXTERNAL_DIR),
             PrepareVirtualEnvCommand(self.devtools_python_requirements),
             self.make_python_stage_command('node', platform=platform, phase=phase),
             ]

    def _get_node_label(self, base_label):
        if self.in_assist_mode:
            suffix = 'psa'
        else:
            suffix = self.project_id
        return '{}-{}'.format(base_label, suffix)

    @property
    def _unstash_results_command_list(self):
        for customization in self.requested_customization_list:
            for platform in self.requested_platform_list:
                stash_name = BUILD_INFO_STASH_NAME_FORMAT.format(customization, platform)
                yield UnstashCommand(stash_name, ignore_missing=True)  # unstash platform build info
                for t in ['distributive', 'update', 'unit_tests', 'qtpdb', 'misc']:
                    name = 'dist-%s-%s-%s' % (customization, platform, t)
                    dir = 'dist'
                    subdir = self._make_artifact_subdir(t, customization, platform)
                    if subdir:
                        dir = os.path.join(dir, subdir)
                    yield UnstashCommand(name, dir, ignore_missing=True)

    def _make_artifact_subdir(self, t, customization, platform):
        if t in ['unit_tests', 'misc']:
            return os.path.join(t, customization, platform)
        if self.must_store_artifacts_in_different_customization_dirs:
            return customization
        else:
            return None

    def _make_workspace_name(self, job_name):
        workspace_name = '{}-{}-{}'.format(self.project_id, self.nx_vms_branch_name, job_name)
        if self.in_assist_mode:
            return 'psa-{}-{}'.format(self.jenkins_env.job_name, workspace_name)
        else:
            return workspace_name

    # build_webadmin ===============================================================================
    def stage_build_webadmin(self):
        job = BuildWebAdminJob(
            self.credentials.rdep_publish,
            self.workspace_dir,
            self._create_junk_shop_repository(platform=WEBADMIN_PLATFORM_NAME),
            )
        build_webadmin = self.params.build_webadmin is None or self.params.build_webadmin
        deploy_webadmin = self.params.deploy_webadmin is None or self.params.deploy_webadmin
        command_list = job.run(
            do_build=build_webadmin,
            deploy=deploy_webadmin,
            deploy_for_version=self.deploy_webadmin_for_version,
            )
        return command_list


    # node =========================================================================================
    def stage_node(self, platform, phase=1):
        log.info('Node stage: node=%s, phase#%s, platform=%s', self.current_node, phase, platform)

        if self.clean_stamps.check_must_clean_node():
            assert phase == 1, repr(phase)  # must never happen on phase 2
            return [CleanDirCommand()] + self._make_node_stage_command_list(platform, phase=2)

        clean_build = self._is_rebuild_required()
        return [self.make_python_stage_command('build', platform=platform, customization_idx=0, clean_build=clean_build)]


    def stage_build(self, platform, customization_idx, clean_build):
        customization = self.requested_customization_list[customization_idx]
        stash_command_list = self._run_build_job(platform, customization, clean_build)
        customization_idx = customization_idx + 1
        if customization_idx < len(self.requested_customization_list):
            return stash_command_list + [
                self.make_python_stage_command(
                    'build', platform=platform, customization_idx=customization_idx, clean_build=False)
                ]
        else:
            return stash_command_list

    def _run_build_job(self, platform, customization, clean_build):
        platform_config = self.config.platforms[platform]
        build_tests = True  # always build - we need appserver2_ut for functional tess
        run_unit_tests = self.params.run_unit_tests and platform_config.should_run_unit_tests
        build_parameters = self._make_build_parameters(customization, platform)
        job = BuildNodeJob(
            cmake_version=self.config.build.cmake_version,
            executor_number=self.jenkins_env.executor_number,
            db_config=self.db_config,
            is_unix=self.is_unix,
            workspace_dir=self.workspace_dir,
            build_parameters=build_parameters,
            platform_config=platform_config,
            branch_config=self.branch_config,
            platform_branch_config=self.branch_config.platforms.get(platform),
            webadmin_external_dir=os.path.join(self.workspace_dir, WEBADMIN_EXTERNAL_DIR),
            hardware_signing=self.is_hardware_signing_enabled(customization, platform),
            )
        stash_command_list = job.run(self.params.do_build, clean_build, self.custom_cmake_args, build_tests, run_unit_tests, self.config.unit_tests.timeout)
        return stash_command_list

    def _is_rebuild_required(self):
        if self.clean_stamps.must_do_clean_build(self.params):
            return True
        nx_vms_scm_info = self.scm_info['nx_vms']
        if not nx_vms_scm_info.prev_revision:
            log.info('Unable to determine previous revision for nx_vms project; will do full rebuild')
            return True
        changes = load_hg_changes(
            repository_dir=os.path.join(self.workspace_dir, 'nx_vms'),
            prev_revision=nx_vms_scm_info.prev_revision,
            current_revision=nx_vms_scm_info.revision,
            )
        if self._do_paths_match_rebuild_cause_pattern('added', changes.added_file_list):
            return True
        if self._do_paths_match_rebuild_cause_pattern('removed', changes.removed_file_list):
            return True
        return False

    def _do_paths_match_rebuild_cause_pattern(self, change_kind, path_list):
        for path in path_list:
            for pattern in self.config.build.rebuild_cause_file_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    log.info('File %r is %s since last build, matching rebuild cause pattern %r; will do full rebuild',
                             path, change_kind, pattern)
                    return True
        return False


    # finalize =====================================================================================
    def stage_finalize(self):
        self.db_config.bind(models.db)
        platform_build_info_map = dict(self._load_platform_build_info_map())  # (customization, platform) -> platform build info
        email_sender = EmailSender(self.config)
        with db_session:
            build_info = self._load_build_info()
            build_info_path = self._save_build_info_artifact(platform_build_info_map, build_info)
            email_recipient_list = self.make_email_recipient_list(build_info)
            subject_and_html = email_sender.render_email(build_info, email_recipient_list, test_mode=self.in_assist_mode)
            command_list = (
                self._make_artifact_archiving_command_list(build_info_path) +
                self.make_postprocess_command_list(build_info.failed_build_platform_list) +
                self._make_set_build_result_command_list(build_info))
        self.post_process(build_info, build_info_path, platform_build_info_map)
        email_sender.send_email(self.credentials.service_email, subject_and_html, email_recipient_list)
        return command_list

    def post_process(self, build_info, build_info_path, platform_build_info_map):
        pass

    @abc.abstractmethod
    def make_email_recipient_list(self, build_info):
        pass

    def make_postprocess_command_list(self, failed_build_platform_list):
        return []

    @property
    def build_user_email_list(self):
        build_user = self.jenkins_env.build_user
        if build_user:
            return ['{} <{}>'.format(build_user.full_name, build_user.email)]
        else:
            return []

    def _load_platform_build_info_map(self):
        for customization in self.requested_customization_list:
            for platform in self.requested_platform_list:
                file_name = BUILD_INFO_FILE_NAME_FORMAT.format(customization, platform)
                if not os.path.exists(file_name):
                    log.warning('Build info for %s/%s is missing (probably due to failed CI subjob); skipping.',
                                    customization, platform)
                    continue
                with open(file_name) as f:
                    yield ((customization, platform), PlatformBuildInfo.from_dict(yaml.load(f)))

    def _load_build_info(self):
        loader = BuildInfoLoader.from_project_branch_num(
            project_name=self.project_name,
            branch_name=self.nx_vms_branch_name,
            build_num=self.jenkins_env.build_number,
            )
        return loader.load_build_platform_list()

    # build_info file left along with artifacts
    def _save_build_info_artifact(self, platform_build_info_map, build_info):
        version_customization = None
        version_platform = None
        version = None
        file_list = []
        for (customization, platform), platform_build_info in platform_build_info_map.items():
            if platform_build_info.is_succeeded:
                if version is None:
                    version = platform_build_info.version
                    version_customization = customization
                    version_platform = platform
                else:
                    assert platform_build_info.version == version, (
                        'Different platforms/customizations ended up with different versions: %s/%s: %r != %s/%s: %r'
                        % (version_customization, version_platform, version,
                               customization, platform, platform_build_info.version))
            for t, artifact_list in platform_build_info.typed_artifact_list.items():
                subdir = self._make_artifact_subdir(t, customization, platform)
                for fname in artifact_list:
                    if subdir:
                        path = os.path.join(subdir, fname)
                    else:
                        path = fname
                    file_list.append(dict(
                        path=path,
                        type=t,
                        customization=customization,
                        platform=platform))
        build_info = dict(
            project=self.project_name,
            branch=self.nx_vms_branch_name,
            build_num=self.jenkins_env.build_number,
            version=version,
            platform_list=self.requested_platform_list,
            customization_list=self.requested_customization_list,
            cloud_group=self.cloud_group,
            failed_build_platform_list=map(str, build_info.failed_build_platform_list),  # avoid !!python/unicode in yaml
            failed_tests_platform_list=map(str, build_info.failed_tests_platform_list),
            file_list=file_list,
            )
        path = BUILD_INFO_FILE
        with open(path, 'w') as f:
            yaml.dump(build_info, f, default_flow_style=False)
        if version:
            with open(VERSION_FILE, 'w') as f:
                f.write(version)
        return path

    def _make_artifact_archiving_command_list(self, build_info_path):
        return [
            ArchiveArtifactsCommand([build_info_path]),
            ArchiveArtifactsCommand(['**'], 'dist'),
            ]

    def _make_set_build_result_command_list(self, build_info):
        if build_info.has_failed_builds:
            build_result = SetBuildResultCommand.brFAILURE
        else:
            return []
        return [SetBuildResultCommand(build_result)]
