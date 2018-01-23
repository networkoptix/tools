# Base class for jenkins projects

import logging
import os.path
import yaml

from cached_property import cached_property

from utils import is_list_inst
from command import (
    Command,
    StashCommand,
    UnstashCommand,
    CheckoutCommand,
    PythonStageCommand,
    StringProjectParameter,
    )
from config import BranchConfig

log = logging.getLogger(__name__)


JUNK_SHOP_DIR = 'devtools/ci/junk_shop'
BRANCH_CONFIG_PATH = 'nx_vms/ci/config.yaml'


class JenkinsProject(object):

    def __init__(self, input_state, in_assist_mode):
        self.state = input_state
        self.config = self.state.config
        self.params = self.state.params
        self.jenkins_env = self.state.jenkins_env
        self.current_node = self.state.current_node
        self.current_command = self.state.current_command
        self.is_unix = self.state.is_unix
        self.workspace_dir = self.state.workspace_dir
        self.scm_info = self.state.scm_info
        self.credentials = self.state.credentials
        self.in_assist_mode = in_assist_mode

    def run(self, stage_id):
        stage_method = self._get_stage_method(stage_id)
        assert stage_method, 'Unknown stage: %r' % stage_id
        command_list = stage_method(**self.current_command.custom_info)
        assert command_list is None or is_list_inst(command_list, Command), (
            'Method %r must return Command instance list or None, but returned: %r' % (method_name, command_list))
        return self.state.make_output_state(command_list)

    def _get_stage_method(self, stage_id):
        method_name = 'stage_%s' % stage_id
        return getattr(self, method_name, None)

    def make_python_stage_command(self, stage_id, python_path_list=None, **kw):
        assert self._get_stage_method(stage_id), 'Unknown stage: %r' % stage_id
        python_path_list = [JUNK_SHOP_DIR] + (python_path_list or [])
        return PythonStageCommand(
            self.project_id, stage_id, self.in_assist_mode, python_path_list, **kw)

    @property
    def prepare_devtools_command(self):
        if self.in_assist_mode:
            return UnstashCommand('devtools')
        else:
            return CheckoutCommand('devtools')

    @property
    def devtools_python_requirements(self):
        return [
            'devtools/ci/projects/requirements.txt',
            os.path.join(JUNK_SHOP_DIR, 'requirements.txt'),
            ]

    @property
    def default_parameters(self):
        if self.in_assist_mode:
            return [
                StringProjectParameter('project', 'project id to test', default_value=self.project_id),
                ]
        else:
            return []

    @cached_property
    def branch_config(self):
        if os.path.exists(BRANCH_CONFIG_PATH):
            with open(BRANCH_CONFIG_PATH) as f:
                config = BranchConfig.from_dict(yaml.load(f))
        else:
            config = BranchConfig.make_default()
        config.report()
        return config
