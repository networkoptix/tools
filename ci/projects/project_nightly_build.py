# trigger clean ci build jobs at night

import logging

from project_nx_vms import NxVmsProject
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


class NightlyBuildProject(NxVmsProject):

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
        return '{}/{}'.format(DOWNSTREAM_PROJECT, self.nx_vms_branch_name)

    def stage_set_status(self):
        result = self.state.job_result[self.downstream_job]
        return [SetBuildResultCommand(result)]
