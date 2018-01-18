# trigger clean ci build jobs at night

import logging

from project import JenkinsProject
from command import (
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
    BooleanParameterValue,
    BuildJobCommand,
    SetBuildResultCommand,
    )

log = logging.getLogger(__name__)


DOWNSTREAM_PROJECT = 'ci'
DAYS_TO_KEEP_OLD_BUILDS = 30
DEFAULT_ASSIST_MODE_VMS_BRANCH = 'vms_3.2_dev'


class NightlyBuildProject(JenkinsProject):

    project_id = 'nightly_build'

    def stage_init(self):
        commands = [self.make_project_properties_command()]
        if self.params.action == 'build':
            commands += [
                self.make_build_job_command(),
                self.make_python_stage_command('set_status'),
                ]
        return commands

    def make_project_properties_command(self):
        parameters = self.default_parameters + [
            ChoiceProjectParameter('action', 'Action to perform: build or just update project properties',
                                   ['build', 'update_properties']),
            ]
        if self.in_assist_mode:
            parameters += [
                StringProjectParameter('branch', 'nx_vms branch to checkout and build',
                                       default_value=DEFAULT_ASSIST_MODE_VMS_BRANCH),
                ]
        return SetProjectPropertiesCommand(
            parameters=parameters,
            enable_concurrent_builds=False,
            days_to_keep_old_builds=DAYS_TO_KEEP_OLD_BUILDS,
            cron=self.config.ci.nightly_schedule,
            )

    def make_build_job_command(self):
        parameters = [
            BooleanParameterValue('clean', True),
            ]
        return BuildJobCommand(
            job=self.downstream_job,
            parameters=parameters,
            )

    @property
    def downstream_job(self):
        return '{}/{}'.format(DOWNSTREAM_PROJECT, self.branch_name)

    @property
    def branch_name(self):
        if self.in_assist_mode:
            return self.params.branch or DEFAULT_ASSIST_MODE_VMS_BRANCH
        else:
            assert self.jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return self.jenkins_env.branch_name

    def stage_set_status(self):
        result = self.state.job_result[self.downstream_job]
        return [SetBuildResultCommand(result)]
