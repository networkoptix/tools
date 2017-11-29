import logging
import os.path
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
    )
from cmake import CMake
from build import CMakeBuilder
from junk_shop import DbConfig, BuildParameters, store_output_and_exit_code


log = logging.getLogger(__name__)


JUNK_SHOP_DIR = 'devtools/ci/junk_shop'


class CiProject(JenkinsProject):

    project_id = 'ci'
    platforms = ['linux-x64', 'mac', 'win-x64']
    # platforms = ['linux-x64']

    def stage_init(self, input):
        return input.make_output_state(command_list=[
            NodeCommand('linux', command_list=[
                # CleanDirCommand(),
                self.prepare_devtools_command(),
                CheckoutScmCommand('jenkins'),
                # CheckoutCommand('nx_vms', 'vms'),
                PrepareVirtualEnvCommand([
                    'devtools/ci/projects/requirements.txt',
                    os.path.join(JUNK_SHOP_DIR, 'requirements.txt'),
                    ]),
                self.make_python_stage_command('report_input', python_path_list=[JUNK_SHOP_DIR]),
                ])])

    def stage_report_input(self, input):
        input.report()

    def stage_init(self, input):
        job_list = [self._make_platform_job(input, platform) for platform in self.platforms]
        return input.make_output_state([
            ParallelCommand(job_list),
            ])

    def _make_platform_job(self, input, platform):
        nx_vms_scm_info = input.scm_info['nx_vms']
        platform_config = input.config.platforms[platform]
        node = platform_config.build_node
        workspace_dir = self._make_workspace_dir(nx_vms_scm_info.branch, platform)
        job_command_list = [
            # CleanDirCommand(),
            self.prepare_devtools_command(),
            CheckoutCommand('nx_vms', 'vms'),
            PrepareVirtualEnvCommand([
                'devtools/ci/projects/requirements.txt',
                os.path.join(JUNK_SHOP_DIR, 'requirements.txt'),
                ]),
            self.make_python_stage_command('node', python_path_list=[JUNK_SHOP_DIR], platform=platform),
            ]
        return ParallelJob(platform, [NodeCommand(node, workspace_dir, job_command_list)])

    def _make_workspace_dir(self, branch, platform):
        if self.in_assist_mode:
            return 'psa-vfedorov-%s' % platform
        else:
            return 'ci-%s-%s' % (branch, platform)

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

        cmake = CMake('3.9.6')
        cmake.ensure_required_cmake_operational()

        clean_build = False
        build_params = BuildParameters(
            project=self.project_id,
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
        builder = CMakeBuilder(cmake)
        build_results = builder.build('nx_vms', 'build', build_params, clean_build, junk_shop_db_config)

    def _make_junk_shop_db_config(self, input):
        user, password = input.credentials.junk_shop_db.split(':')
        return DbConfig(input.config.junk_shop.db_host, user, password)
