# base project for CI and Release projects

import logging
import os.path
import abc
import glob
import re
import yaml

from pony.orm import db_session

from junk_shop import (
    models,
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    run_unit_tests,
)
from utils import ensure_dir_missing, prepare_empty_dir
from project_nx_vms import BUILD_INFO_FILE, NxVmsProject
from command import (
    CleanDirCommand,
    PrepareVirtualEnvCommand,
    ArchiveArtifactsCommand,
    NodeCommand,
    ParallelJob,
    BooleanProjectParameter,
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
    StashCommand,
    UnstashCommand,
    SetBuildResultCommand,
)
from cmake import CMake
from build import CMakeBuilder
from clean_stamps import CleanStamps
from diff_parser import load_hg_changes

log = logging.getLogger(__name__)


CMAKE_VERSION = '3.10.2'


# build and run tests on single node for single customization/platofrm
class BuildNodeJob(object):

    def __init__(self,
                 executor_number,
                 db_config,
                 is_unix,
                 workspace_dir,
                 build_parameters,
                 platform_config,
                 platform_branch_config,
                 ):
        self._executor_number = executor_number
        self._db_config = db_config
        self._is_unix = is_unix
        self._workspace_dir = workspace_dir
        self._platform_config = platform_config
        self._platform_branch_config = platform_branch_config
        self._error_list = []
        self._repository = DbCaptureRepository(db_config, build_parameters)

    def run(self, clean_build, build_tests, run_unit_tests, unit_tests_timeout):
        build_info = self._build(clean_build, build_tests)
        if build_info.is_succeeded and run_unit_tests:
            self._run_unit_tests(build_info, unit_tests_timeout)
        if not build_info.is_succeeded:
            return None
        command_list = self._make_post_build_actions(build_info)
        self._save_errors_artifact(build_info)
        return command_list

    @property
    def _customization(self):
        return self._repository.build_parameters.customization

    @property
    def _platform(self):
        return self._repository.build_parameters.platform

    def _build(self, clean_build, build_tests):
        cmake = CMake(CMAKE_VERSION)
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(self._executor_number, self._platform_config, self._platform_branch_config, self._repository, cmake)
        build_info = builder.build('nx_vms', 'build', build_tests, clean_build)
        return build_info

    def _run_unit_tests(self, build_info, timeout):
        if self._is_unix:
            ext = ''
        else:
            ext = '.exe'
        unit_test_mask_list = os.path.join(build_info.unit_tests_bin_dir, '*_ut%s' % ext)
        test_binary_list = [os.path.basename(path) for path in glob.glob(unit_test_mask_list)]
        if not test_binary_list:
            self._add_error('No unit tests were produced matching masks: {}'.format(unit_test_mask_list))
            return
        unit_tests_dir = os.path.join(self._workspace_dir, 'unit_tests')
        bin_dir = os.path.abspath(build_info.unit_tests_bin_dir)
        prepare_empty_dir(unit_tests_dir)
        log.info('Running unit tests in %r: %s', unit_tests_dir, ', '.join(test_binary_list))
        logging.getLogger('junk_shop.unittest').setLevel(logging.INFO)  # prevent unit tests from logging stdout/stderr
        is_passed = run_unit_tests(
            self._repository, build_info.current_config_path, unit_tests_dir, bin_dir, test_binary_list, timeout)
        log.info('Unit tests are %s', 'passed' if is_passed else 'failed')

    def _make_post_build_actions(self, build_info):
        return (
            self._make_stash_command_list(
                'dist-%s-%s-distributive' % (self._customization, self._platform),
                build_info.artifacts_dir, self._platform_config.distributive_mask_list,
                exclude_list=self._platform_config.update_mask_list) +
            self._make_stash_command_list(
                'dist-%s-%s-update' % (self._customization, self._platform),
                build_info.artifacts_dir, self._platform_config.update_mask_list)
            )

    def _make_stash_command_list(self, stash_name, artifacts_dir, artifact_mask_list, exclude_list=None):
        artifact_list = list(self._list_artifacts(artifacts_dir, artifact_mask_list, exclude_list))
        if not artifact_list:
            error = 'No artifacts were produced matching masks: {}'.format(', '.join(artifact_mask_list))
            self._add_error(error)
            return []
        return [StashCommand(stash_name, artifact_list, artifacts_dir)]
 
    def _list_artifacts(self, artifacts_dir, include_list, exclude_list=None):
        if exclude_list:
            exclude_set = set(self._list_artifacts(artifacts_dir, exclude_list))
        else:
            exclude_set = set()
        for mask in include_list:
            for path in glob.glob(os.path.join(artifacts_dir, mask)):
                relative_path = os.path.relpath(path, artifacts_dir)
                if relative_path not in exclude_set:
                    yield relative_path

    def _add_error(self, error):
        log.error(error)
        self._error_list.append(error)

    @db_session
    def _save_errors_artifact(self, build_info):
        if not self._error_list:
            return
        run = models.Run[build_info.run_id]
        self._repository.add_artifact(
            run, 'errors', 'errors', self._repository.artifact_type.output, '\n'.join(self._error_list), is_error=True)


class BuildProject(NxVmsProject):

    __metaclass__ = abc.ABCMeta

    def __init__(self, input_state, in_assist_mode):
        NxVmsProject.__init__(self, input_state, in_assist_mode)
        self._build_error_list = []
        self.clean_stamps = CleanStamps(self.state)

    def stage_init(self):
        command_list = [self.set_project_properties_command]

        if self.in_assist_mode and self.params.stage:
            command_list += [
                self.make_python_stage_command(self.params.stage),
                ]
        elif self.must_actually_do_build():
            command_list += self.initial_stash_nx_vms_command_list + self.prepare_nx_vms_command_list + [
                self.make_python_stage_command('prepare_for_build'),
                ]
        return command_list

    def must_actually_do_build(self):
        return self.params.action == 'build'

    def stage_report_state(self):
        self.state.report()

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

    @property
    def set_project_properties_command(self):
        return SetProjectPropertiesCommand(
            parameters=self.get_project_parameters(),
            enable_concurrent_builds=False,
            days_to_keep_old_builds=self.days_to_keep_old_builds,
            )

    def get_project_parameters(self):
        parameters = self.default_parameters
        if self.in_assist_mode:
            parameters += [
                StringProjectParameter('stage', 'stage to run', default_value=''),
                ]
        parameters += [
                    ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                               ['build', 'update_properties']),
                    BooleanProjectParameter('run_unit_tests', 'Run unit tests', default_value=self.run_unit_tests_by_default),
                    BooleanProjectParameter('clean_build', 'Build from scratch', default_value=False),
                    BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
                    BooleanProjectParameter('clean_only', 'Clean workspaces instead build', default_value=False),
                    BooleanProjectParameter('add_qt_pdb', 'Tell me if you know what this parameter means', default_value=False),
                    ]
        return parameters

    @property
    def run_unit_tests_by_default(self):
        return True

    @property
    def project_name(self):
        if self.in_assist_mode:
            return 'assist-ci-%s' % self.jenkins_env.job_name
        else:
            return self.project_id

    def init_build_info(self):
        repository = self._create_junk_shop_repository()
        revision_info = update_build_info(repository, 'nx_vms')
        self.scm_info['nx_vms'].set_prev_revision(revision_info.prev_revision)  # will be needed later

    def _create_junk_shop_repository(self):
        return DbCaptureRepository(self.db_config, self._build_parameters(self.customization))

    def _build_parameters(self, customization, platform=None):
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

    def make_parallel_job(self, job_name, workspace_dir, platform, **kw):
        platform_config = self.config.platforms[platform]
        node = self._get_build_node_label(platform_config)
        job_command_list = []
        if self.params.clean or self.params.clean_only:
            job_command_list += [
                CleanDirCommand(),
                ]
        if not self.params.clean_only:
            job_command_list += self.make_node_stage_command_list(platform=platform, **kw)
        return ParallelJob(job_name, [NodeCommand(node, workspace_dir, job_command_list)])

    def _get_build_node_label(self, platform_config):
        if self.in_assist_mode:
            suffix = 'psa'
        else:
            suffix = self.project_id
        return '{}-{}'.format(platform_config.build_node, suffix)

    def make_node_stage_command_list(self, **kw):
        return self.prepare_devtools_command_list + self.prepare_nx_vms_command_list + [
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            self.make_python_stage_command('node', **kw),
            ]

    def run_build_node_job(self, customization, platform):
        platform_config = self.config.platforms[platform]
        platform_branch_config = self.branch_config.platforms.get(platform)
        clean_build = self._is_rebuild_required()
        build_tests = self.params.run_unit_tests is None or self.params.run_unit_tests
        run_unit_tests = self.params.run_unit_tests and platform_config.should_run_unit_tests
        build_parameters = self._build_parameters(customization, platform)
        job = BuildNodeJob(
            self.jenkins_env.executor_number,
            self.db_config,
            self.is_unix,
            self.workspace_dir,
            build_parameters,
            platform_config,
            platform_branch_config,
            )
        command_list = job.run(clean_build, build_tests, run_unit_tests, self.config.unit_tests.timeout)
        return command_list
            
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

    def do_final_processing(self, build_info, separate_customizations):
        ensure_dir_missing('dist')
        command_list = []
        for customization in self.requested_customization_list:
            for platform in self.requested_platform_list:
                for suffix in ['distributive', 'update']:
                    name = 'dist-%s-%s-%s' % (customization, platform, suffix)
                    dir = os.path.join('dist', name)
                    if separate_customizations:
                        dir = os.path.join(dir, customization)
                    command_list.append(UnstashCommand(name, dir, ignore_missing=True))
        build_info_path = self._save_build_info_artifact()
        command_list += [
            ArchiveArtifactsCommand([build_info_path]),
            ArchiveArtifactsCommand(['dist/**']),
            ]
        command_list += self._make_set_build_result_command_list(build_info)
        return command_list

    def _save_build_info_artifact(self):
        build_info = dict(
            project=self.project_name,
            branch=self.nx_vms_branch_name,
            build_num=self.jenkins_env.build_number,
            platform_list=self.requested_platform_list,
            customization_list=self.requested_customization_list,
            cloud_group=self.cloud_group,
            )
        path = BUILD_INFO_FILE
        with open(path, 'w') as f:
            yaml.dump(build_info, f)
        return path

    def _make_set_build_result_command_list(self, build_info):
        if build_info.has_failed_builds:
            build_result = SetBuildResultCommand.brFAILURE
        elif build_info.has_failed_tests:
            build_result = SetBuildResultCommand.brUNSTABLE
        else:
            return []
        return [SetBuildResultCommand(build_result)]
