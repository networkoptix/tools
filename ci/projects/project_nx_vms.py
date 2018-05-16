# Base class for multibranch projects based on nx_vms repository

from project import JenkinsProject
from command import (
    CheckoutCommand,
    CheckoutScmCommand,
    StashCommand,
    UnstashCommand,
    StringProjectParameter,
    )


DEFAULT_ASSIST_MODE_VMS_BRANCH = 'vms_3.2_dev'
BUILD_INFO_FILE = 'build_info.yaml'


class NxVmsProject(JenkinsProject):

    @property
    def default_parameters(self):
        parameters = super(NxVmsProject, self).default_parameters
        if self.in_assist_mode:
            parameters += [
                StringProjectParameter(
                    'branch', 'nx_vms branch to checkout and use', default_value=DEFAULT_ASSIST_MODE_VMS_BRANCH),
                ]
        return parameters

    @property
    def nx_vms_branch_name(self):
        if self.in_assist_mode:
            return self.params.branch or DEFAULT_ASSIST_MODE_VMS_BRANCH
        else:
            assert self.jenkins_env.branch_name, (
                'This scripts are intented to be used in multibranch projects only;'
                ' env.BRANCH_NAME must be defined')
            return self.jenkins_env.branch_name

    @property
    def initial_stash_nx_vms_command_list(self):
        if self.in_assist_mode:
            return [StashCommand('nx_vms_ci', ['nx_vms/ci/**'])]
        else:
            return []

    def make_prepare_nx_vms_command_list(self, revision=None):
        if self.in_assist_mode:
            branch_name = self.nx_vms_branch_name
            return [
                CheckoutCommand('nx_vms', revision or branch_name),
                UnstashCommand('nx_vms_ci'),
                ]
        elif revision:
            return [CheckoutCommand('nx_vms', revision)]
        else:
            return [CheckoutScmCommand('nx_vms')]
