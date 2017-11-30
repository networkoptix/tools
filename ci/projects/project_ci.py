import logging
import sys
from project import JenkinsProject
from command import (
    ScriptCommand,
    CheckoutCommand,
    CheckoutScmCommand,
    StashCommand,
    UnstashCommand,
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
from junk_shop import (
    DbConfig,
    BuildParameters,
    DbCaptureRepository,
    update_build_info,
    store_output_and_exit_code,
    )

log = logging.getLogger(__name__)


ASSIST_MODE_VMS_BRANCH = 'vms'
DAYS_TO_KEEP_OLD_BUILDS = 10


class CiProject(JenkinsProject):

    project_id = 'ci'

    def stage_init(self, input):
        return input.make_output_state([
            SetProjectPropertiesCommand(
                parameters=[
                    BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
                    StringProjectParameter('branch', 'nx_vms branch to checkout', default_value='vms'),
                    ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                               ['build', 'update_properties']),
                    ],
                enable_concurrent_builds=False,
                days_to_keep_old_builds=10,
                )])

    def _stage_init(self, input):
        return input.make_output_state(command_list=[
            NodeCommand('linux', command_list=[
                # CleanDirCommand(),
                self.prepare_devtools_command(),
                CheckoutScmCommand('jenkins'),
                # CheckoutCommand('nx_vms', 'vms'),
                PrepareVirtualEnvCommand(self.devtools_python_requirements),
                self.make_python_stage_command('report_input'),
                ])])

    def stage_report_input(self, input):
        input.report()

    def stage_init(self, input):
        all_platform_list = sorted(input.config.platforms.keys())
        parameters = [
                    ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                               ['build', 'update_properties']),
                    BooleanProjectParameter('clean', 'Clean workspaces before build', default_value=False),
                    ]
        parameters += [BooleanProjectParameter(platform, 'Build platform %s' % platform, default_value=True)
                           for platform in all_platform_list]
        command_list = [
            SetProjectPropertiesCommand(
                parameters=parameters,
                enable_concurrent_builds=False,
                days_to_keep_old_builds=DAYS_TO_KEEP_OLD_BUILDS,
                ),
            ]
        if input.params.get('action') == 'build':
            command_list.append(self.make_python_stage_command('prepare_for_build'))
        return input.make_output_state(command_list)

    def stage_prepare_for_build(self, input):
        all_platform_list = sorted(input.config.platforms.keys())
        platform_list = [p for p in all_platform_list if input.params.get(p)]
        job_list = [self._make_platform_job(input, platform) for platform in platform_list]
        return input.make_output_state([
            ParallelCommand(job_list),
            ])

    def _make_platform_job(self, input, platform):
        branch_name = self._nx_vms_branch_name(input.jenkins_env)
        platform_config = input.config.platforms[platform]
        node = platform_config.build_node
        workspace_dir = self._make_workspace_dir(branch_name, platform)
        job_command_list = [
            # CleanDirCommand(),
            self.prepare_devtools_command(),
            CheckoutCommand('nx_vms', branch_name),
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            self.make_python_stage_command('node', platform=platform),
            ]
        return ParallelJob(platform, [NodeCommand(node, workspace_dir, job_command_list)])

    def _nx_vms_branch_name(self, jenkins_env):
        if self.in_assist_mode:
            return ASSIST_MODE_VMS_BRANCH
        else:
            assert jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return jenkins_env.branch_name

    def _make_workspace_dir(self, branch_name, platform):
        if self.in_assist_mode:
            return 'psa-vfedorov-%s' % platform
        else:
            return 'ci-%s-%s' % (branch_name, platform)

    def stage_node(self, input):
        log.info('Node stage: %s', input.current_node)
        self._build(input)
        command_list = []
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

    def _build(self, input):
        platform = input.current_command.platform
        nx_vms_scm_info = input.scm_info['nx_vms']
        junk_shop_db_config = self._make_junk_shop_db_config(input)
        clean_build = False
        if self.in_assist_mode:
            project = 'assist-ci-%s' % input.jenkins_env.job_name
        else:
            project = self.project_id
        build_params = BuildParameters(
            project=project,
            platform=platform,
            build_num=input.jenkins_env.build_number,
            branch=nx_vms_scm_info.branch,
            configuration='release',
            cloud_group='test',
            customization='default',
            is_incremental=not clean_build,
            jenkins_url=input.jenkins_env.build_url,
            repository_url=nx_vms_scm_info.repository_url,
            revision=nx_vms_scm_info.revision,
            )
        junk_shop_repository = DbCaptureRepository(junk_shop_db_config, build_params)

        update_build_info(junk_shop_repository, 'nx_vms')

        cmake = CMake('3.9.6')
        cmake.ensure_required_cmake_operational()

        builder = CMakeBuilder(cmake)
        build_results = builder.build('nx_vms', 'build', build_params, clean_build, junk_shop_repository)

    def _make_junk_shop_db_config(self, input):
        user, password = input.credentials.junk_shop_db.split(':')
        return DbConfig(input.config.junk_shop.db_host, user, password)
