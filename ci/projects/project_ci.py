import logging
import os.path
import glob
import sys

from junk_shop import (
    models,
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    store_output_and_exit_code,
    run_unit_tests,
    )
from project import JenkinsProject
from command import (
    ScriptCommand,
    CheckoutCommand,
    CheckoutScmCommand,
    StashCommand,
    UnstashCommand,
    ArchiveArtifactsCommand,
    CleanDirCommand,
    NodeCommand,
    PrepareVirtualEnvCommand,
    ParallelJob,
    ParallelCommand,
    BooleanProjectParameter,
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
    )
from cmake import CMake
from build import CMakeBuilder
from email_sender import EmailSender

log = logging.getLogger(__name__)


DEFAULT_ASSIST_MODE_VMS_BRANCH = 'vms_3.2'
DAYS_TO_KEEP_OLD_BUILDS = 10


class CiProject(JenkinsProject):

    project_id = 'ci'

    def stage_init(self, input):
        all_platform_list = sorted(input.config.platforms.keys())
        command_list = [self._set_project_properties_command(all_platform_list)]
        if self.in_assist_mode and input.params.stage:
            command_list += [
                self.make_python_stage_command(input.params.stage),
                ]
        elif input.params.action == 'build':
            command_list += [
                self._checkout_nx_vms_command(input),
                self.make_python_stage_command('prepare_for_build'),
                ]
        return input.make_output_state(command_list)

    def stage_report_input(self, input):
        input.report()

    def _set_project_properties_command(self, all_platform_list):
        parameters = [
                    ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                               ['build', 'update_properties']),
                    BooleanProjectParameter('clean_build', 'Build from stcatch', default_value=False),
                    BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
                    BooleanProjectParameter('clean_only', 'Clean workspaces instead build', default_value=False),
                    ]
        if self.in_assist_mode:
            parameters += [
                StringProjectParameter('branch', 'nx_vms branch to checkout and build',
                                           default_value=DEFAULT_ASSIST_MODE_VMS_BRANCH),
                StringProjectParameter('stage', 'stage to run', default_value=''),
                ]
        parameters += [BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=True)
                           for platform in all_platform_list]
        return SetProjectPropertiesCommand(
            parameters=parameters,
            enable_concurrent_builds=False,
            days_to_keep_old_builds=DAYS_TO_KEEP_OLD_BUILDS,
            )

    def _checkout_nx_vms_command(self, input):
        if self.in_assist_mode:
            branch_name = self._nx_vms_branch_name(input)
            return CheckoutCommand('nx_vms', branch_name)
        else:
            return CheckoutScmCommand('nx_vms')

    def stage_prepare_for_build(self, input):
        junk_shop_repository = self._create_junk_shop_repository(input)
        update_build_info(junk_shop_repository, 'nx_vms')

        all_platform_list = sorted(input.config.platforms.keys())
        platform_list = [p for p in all_platform_list if input.params.get(p)]
        job_list = [self._make_platform_job(input, platform) for platform in platform_list]
        return input.make_output_state([
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ])

    def _make_platform_job(self, input, platform):
        branch_name = self._nx_vms_branch_name(input)
        platform_config = input.config.platforms[platform]
        node = platform_config.build_node
        workspace_dir = self._make_workspace_dir(input.jenkins_env.job_name, branch_name, platform)
        job_command_list = []
        if input.params.clean or input.params.clean_only:
            job_command_list += [
                CleanDirCommand(),
                ]
        if not input.params.clean_only:
            job_command_list += [
                self.prepare_devtools_command(),
                self._checkout_nx_vms_command(input),
                PrepareVirtualEnvCommand(self.devtools_python_requirements),
                self.make_python_stage_command('node', platform=platform),
                ]
        return ParallelJob(platform, [NodeCommand(node, workspace_dir, job_command_list)])

    def _nx_vms_branch_name(self, input):
        if self.in_assist_mode:
            return input.params.branch or DEFAULT_ASSIST_MODE_VMS_BRANCH
        else:
            assert input.jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return input.jenkins_env.branch_name

    def _project_name(self, input):
        if self.in_assist_mode:
            return 'assist-ci-%s' % input.jenkins_env.job_name
        else:
            return self.project_id

    def _make_workspace_dir(self, job_name, branch_name, platform):
        if self.in_assist_mode:
            return 'psa-%s-%s' % (job_name, platform)
        else:
            return 'ci-%s-%s' % (branch_name, platform)

    def stage_node(self, input):
        log.info('Node stage: %s', input.current_node)
        platform = input.current_command.platform
        junk_shop_repository = self._create_junk_shop_repository(input, platform)

        build_info = self._build(input, junk_shop_repository)
        self._run_unit_tests(input.is_unix, junk_shop_repository, build_info, input.config.ci.timeout)

        command_list = [ArchiveArtifactsCommand(build_info.artifact_mask_list)]
        # command_list = self._list_dirs_commands(input)
        return input.make_output_state(command_list)

    def _list_dirs_commands(self, input):
        if input.is_unix:
            return [
                ScriptCommand('pwd'),
                ScriptCommand('ls -alh'),
                ScriptCommand('ls -alh build'),
                ]
        else:
            return [
                ScriptCommand('dir'),
                ScriptCommand('dir build'),
                ]

    def _create_junk_shop_repository(self, input, platform=None):
        nx_vms_scm_info = input.scm_info['nx_vms']
        project = self._project_name(input)
        is_incremental = not (input.params.clean or input.params.clean_build)
        build_params = BuildParameters(
            project=project,
            platform=platform,
            build_num=input.jenkins_env.build_number,
            branch=nx_vms_scm_info.branch,
            configuration='release',
            cloud_group='test',
            customization='default',
            is_incremental=is_incremental,
            jenkins_url=input.jenkins_env.build_url,
            repository_url=nx_vms_scm_info.repository_url,
            revision=nx_vms_scm_info.revision,
            )
        db_config = self._db_config(input)
        return DbCaptureRepository(db_config, build_params)

    def _db_config(self, input):
        user, password = input.credentials.junk_shop_db.split(':')
        return DbConfig(input.config.junk_shop.db_host, user, password)

    def _build(self, input, junk_shop_repository):
        cmake = CMake('3.9.6')
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(cmake)
        build_info = builder.build('nx_vms', 'build', input.params.clean_build, junk_shop_repository)
        return build_info

    def _run_unit_tests(self, is_unix, junk_shop_repository, build_info, timeout):
        if is_unix:
            ext = ''
        else:
            ext = '.exe'
        test_binary_list = [os.path.basename(path) for path
                                in glob.glob(os.path.join(build_info.unit_tests_bin_dir, '*_ut%s' % ext))]
        log.info('Running unit tests: %s', ', '.join(test_binary_list))
        logging.getLogger('junk_shop.unittest').setLevel(logging.INFO)  # Prevent from logging unit tests stdout/stderr
        is_passed = run_unit_tests(
            junk_shop_repository, build_info.current_config_path, build_info.unit_tests_bin_dir, test_binary_list, timeout)
        log.info('Unit tests are %s', 'passed' if is_passed else 'failed')

    def stage_finalize(self, input):
        nx_vms_scm_info = input.scm_info['nx_vms']
        db_config = self._db_config(input)
        db_config.bind(models.db)
        smtp_password = input.credentials.service_email
        project = self._project_name(input)
        branch = nx_vms_scm_info.branch
        build_num = input.jenkins_env.build_number
        sender = EmailSender(input.config)
        sender.render_and_send_email(smtp_password, project, branch, build_num, test_mode=self.in_assist_mode)
