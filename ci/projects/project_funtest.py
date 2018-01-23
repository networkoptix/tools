# Project for running functional tests.
# Input files (distributives) to test are taken from upstream project artifacts

import logging

from project_nx_vms import BUILD_INFO_FILE, NxVmsProject
from command import (
    StashCommand,
    UnstashCommand,
    CopyArtifactsCommand,
    ScriptCommand,
    CleanDirCommand,
    ParallelCommand,
    StringProjectParameter,
    ChoiceProjectParameter,
    ParallelJob,
    NodeCommand,
    PrepareVirtualEnvCommand,
    SetProjectPropertiesCommand,
    )
from email_sender import EmailSender

log = logging.getLogger(__name__)


UPSTREAM_PROJECT = 'ci'
WORK_DIR = 'work'
DIST_DIR = 'dist'
DIST_STASH = 'dist'


class FunTestProject(NxVmsProject):

    project_id = 'funtest'

    def stage_init(self):
        command_list = [self.set_project_properties_command]

        if self.params.action != 'test':
            return command_list

        job_list = [self.make_parallel_job(platform) for platform in self.requested_platform_list]
        command_list += self.initial_stash_nx_vms_command_list + [
            self.copy_artifacts_command,
            StashCommand(DIST_STASH, ['%s/**' % DIST_DIR]),
            ParallelCommand(job_list),
            self.make_python_stage_command('finalize'),
            ]
        return command_list

    @property
    def set_project_properties_command(self):
        return SetProjectPropertiesCommand(
            parameters=self.get_project_parameters(),
            enable_concurrent_builds=self.config.fun_tests.enable_concurrent_builds,
            days_to_keep_old_builds=self.config.fun_tests.days_to_keep_old_builds,
            )

    def get_project_parameters(self):
        parameters = self.default_parameters + [
            ChoiceProjectParameter('action', 'Action to perform: run tests or just update project properties',
                                       ['test', 'update_properties']),
            StringProjectParameter('tests', 'Which tests to run; by default (empty value) run all', default_value=''),
            StringProjectParameter(
                'build_num', 'Which build to test; by default (empty value) one that triggered this job', default_value=''),
            ]
        return parameters

    @property
    def requested_platform_list(self):
        return self.config.fun_tests.platforms

    def make_parallel_job(self, platform):
        job_command_list = self.prepare_nx_vms_command_list + [
            self.prepare_devtools_command,
            PrepareVirtualEnvCommand(self.devtools_python_requirements),
            UnstashCommand(DIST_STASH),
            self.make_python_stage_command('run_tests'),
            ]
        job_name = platform
        node = self.config.fun_tests.node
        workspace_dir = self.make_workspace_dir(platform)
        return ParallelJob(job_name, [NodeCommand(node, workspace_dir, job_command_list)])

    @property
    def copy_artifacts_command(self):
        if self.params.build_num:
            selector = CopyArtifactsCommand.selSpecificBuild
            try:
                build_num = int(self.params.build_num)
            except ValueError:
                assert False, 'Invalid build_num: %r' % build_num
        else:
            if self.in_assist_mode:
                selector = CopyArtifactsCommand.selCompleted
            else:
                selector = CopyArtifactsCommand.selUpstream
            build_num = None
        upstream_project_name = UPSTREAM_PROJECT + '/' + self.nx_vms_branch_name
        return CopyArtifactsCommand(upstream_project_name, DIST_DIR, selector, build_num)

    def make_workspace_dir(self, platform):
        if self.in_assist_mode:
            return 'psa-{}-{}-{}'.format(self.project_id, self.jenkins_env.job_name, platform)
        else:
            return '{}-{}-{}'.format(self.project_id, self.nx_vms_branch_name, platform)

    def stage_run_tests(self, platform):
        log.info('Running functional tests for platform %r; executor#%s', platform, self.jenkins_env.executor_number)

    def stage_finalize(self):
        pass
