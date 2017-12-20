# base project for CI and Release projects

import logging

from project import JenkinsProject
from command import (
    CheckoutCommand,
    CheckoutScmCommand,
    UnstashCommand,
    BooleanProjectParameter,
    StringProjectParameter,
    ChoiceProjectParameter,
    SetProjectPropertiesCommand,
)

log = logging.getLogger(__name__)


DEFAULT_ASSIST_MODE_VMS_BRANCH = 'vms_3.2'


class BuildProject(JenkinsProject):

    days_to_keep_old_builds = 10

    def __init__(self, input_state, in_assist_mode):
        JenkinsProject.__init__(self, input_state, in_assist_mode)
        self._build_error_list = []

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

    def stage_report_state(self):
        self.state.report()

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
                    ]
        return parameters

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
