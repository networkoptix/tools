# base project for CI and Release projects

import logging
import os.path
import glob

from pony.orm import db_session

from junk_shop import (
    models,
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    run_unit_tests,
)

from project import JenkinsProject
from command import (
    CheckoutCommand,
    CheckoutScmCommand,
    CleanDirCommand,
    UnstashCommand,
    PrepareVirtualEnvCommand,
    ArchiveArtifactsCommand,
    NodeCommand,
    ParallelJob,
    BooleanProjectParameter,
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
    SetBuildResultCommand,
)
from cmake import CMake
from build import CMakeBuilder
from clean_stamps import CleanStamps

log = logging.getLogger(__name__)


DEFAULT_ASSIST_MODE_VMS_BRANCH = 'vms_3.2'


class BuildProject(JenkinsProject):

    days_to_keep_old_builds = 10

    def __init__(self, input_state, in_assist_mode):
        JenkinsProject.__init__(self, input_state, in_assist_mode)
        self._build_error_list = []
        self.clean_stamps = CleanStamps(self.state)

    def stage_init(self):
        command_list = [self.set_project_properties_command]

        if self.in_assist_mode and self.params.stage:
            command_list += [
                self.make_python_stage_command(self.params.stage),
                ]
        elif self.params.action == 'build':
            command_list += self.initial_stash_command_list + self.prepare_nx_vms_command_list + [
                self.make_python_stage_command('prepare_for_build'),
                ]
        return command_list

    def init_build_info(self):
        junk_shop_repository = self.create_junk_shop_repository()
        update_build_info(junk_shop_repository, 'nx_vms')

    def stage_report_state(self):
        self.state.report()

    @property
    def db_config(self):
        user, password = self.credentials.junk_shop_db.split(':')
        return DbConfig(self.config.junk_shop.db_host, user, password)

    @property
    def all_platform_list(self):
        return sorted(self.config.platforms.keys())

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
                StringProjectParameter('branch', 'nx_vms branch to checkout and build',
                                           default_value=DEFAULT_ASSIST_MODE_VMS_BRANCH),
                StringProjectParameter('stage', 'stage to run', default_value=''),
                ]
        parameters += [
                    ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                               ['build', 'update_properties']),
                    BooleanProjectParameter('clean_build', 'Build from scratch', default_value=False),
                    BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
                    BooleanProjectParameter('clean_only', 'Clean workspaces instead build', default_value=False),
                    BooleanProjectParameter('add_qt_pdb', 'Tell me if you known what this parameter means', default_value=False),
                    ]
        return parameters

    @property
    def project_name(self):
        if self.in_assist_mode:
            return 'assist-ci-%s' % self.jenkins_env.job_name
        else:
            return self.project_id

    @property
    def nx_vms_branch_name(self):
        if self.in_assist_mode:
            return self.params.branch or DEFAULT_ASSIST_MODE_VMS_BRANCH
        else:
            assert self.jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return self.jenkins_env.branch_name

    def make_parallel_job(self, job_name, workspace_dir, platform, **kw):
        platform_config = self.config.platforms[platform]
        node = platform_config.build_node
        job_command_list = []
        if self.params.clean or self.params.clean_only:
            job_command_list += [
                CleanDirCommand(),
                ]
        if not self.params.clean_only:
            job_command_list += self.make_node_stage_command_list(platform=platform, **kw)
        return ParallelJob(job_name, [NodeCommand(node, workspace_dir, job_command_list)])

    def make_node_stage_command_list(self, **kw):
        return [
            self.prepare_devtools_command,
            ] + self.prepare_nx_vms_command_list + [
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            self.make_python_stage_command('node', **kw),
            ]

    @property
    def prepare_nx_vms_command_list(self):
        if self.in_assist_mode:
            branch_name = self.nx_vms_branch_name
            return [
                CheckoutCommand('nx_vms', branch_name),
                UnstashCommand('nx_vms_ci'),
                ]
        else:
            return [CheckoutScmCommand('nx_vms')]

    def create_junk_shop_repository(self, **kw):
        build_parameters = self.create_build_parameters(**kw)
        return DbCaptureRepository(self.db_config, build_parameters)

    def create_build_parameters(self, platform, customization, release, cloud_group):
        nx_vms_scm_info = self.scm_info['nx_vms']
        project = self.project_name
        is_incremental = not (self.params.clean or self.params.clean_build)
        return BuildParameters(
            project=project,
            platform=platform,
            build_num=self.jenkins_env.build_number,
            release=release,
            branch=nx_vms_scm_info.branch,
            configuration='release',
            cloud_group=cloud_group,
            customization=customization,
            add_qt_pdb=self.params.add_qt_pdb,
            is_incremental=is_incremental,
            jenkins_url=self.jenkins_env.build_url,
            repository_url=nx_vms_scm_info.repository_url,
            revision=nx_vms_scm_info.revision,
            )

    def _build(self, junk_shop_repository, platform_branch_config, platform_config, clean_build):
        cmake = CMake('3.9.6')
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(platform_config, platform_branch_config, cmake)
        build_info = builder.build(junk_shop_repository, 'nx_vms', 'build', clean_build)
        return build_info

    def add_build_error(self, error):
        log.error(error)
        self._build_error_list.append(error)

    @db_session
    def save_build_errors_artifact(self, repository, build_info):
        if not self._build_error_list:
            return
        run = models.Run[build_info.run_id]
        repository.add_artifact(
            run, 'errors', 'errors', repository.artifact_type.output, '\n'.join(self._build_error_list), is_error=True)

    def post_build_actions(self, junk_shop_repository, build_info):
        if not build_info.is_succeeded:
            return None
        if self.has_artifacts(build_info.artifact_mask_list):
            command_list = [ArchiveArtifactsCommand(build_info.artifact_mask_list)]
        else:
            error = 'No artifacts were produced matching masks: {}'.format(', '.join(build_info.artifact_mask_list))
            self.add_build_error(error)
            command_list = []

        self.save_build_errors_artifact(junk_shop_repository, build_info)
        return command_list

    def has_artifacts(self, artifact_mask_list):
        for mask in artifact_mask_list:
            if glob.glob(mask):
                return True
        else:
            return False

    def run_unit_tests(self, junk_shop_repository, build_info, timeout):
        if self.is_unix:
            ext = ''
        else:
            ext = '.exe'
        unit_test_mask_list = os.path.join(build_info.unit_tests_bin_dir, '*_ut%s' % ext)
        test_binary_list = [os.path.basename(path) for path in glob.glob(unit_test_mask_list)]
        if not test_binary_list:
            self.add_build_error('No unit tests were produced matching masks: {}'.format(unit_test_mask_list))
            return
        log.info('Running unit tests: %s', ', '.join(test_binary_list))
        logging.getLogger('junk_shop.unittest').setLevel(logging.INFO)  # Prevent from logging unit tests stdout/stderr
        is_passed = run_unit_tests(
            junk_shop_repository, build_info.current_config_path, build_info.unit_tests_bin_dir, test_binary_list, timeout)
        log.info('Unit tests are %s', 'passed' if is_passed else 'failed')

    def make_set_build_result_command_list(self, build_info):
        if build_info.has_failed_builds:
            build_result = SetBuildResultCommand.brFAILURE
        elif build_info.has_failed_tests:
            build_result = SetBuildResultCommand.brUNSTABLE
        else:
            return None
        return [SetBuildResultCommand(build_result)]
