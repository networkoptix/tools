import logging
import os.path
from utils import is_list_inst
from command import Command, UnstashCommand, CheckoutCommand, PythonStageCommand, StringProjectParameter

log = logging.getLogger(__name__)


JUNK_SHOP_DIR = 'devtools/ci/junk_shop'


class JenkinsProject(object):

    def __init__(self, input_state, in_assist_mode):
        self.state = input_state
        self.config = self.state.config
        self.params = self.state.params
        self.jenkins_env = self.state.jenkins_env
        self.current_node = self.state.current_node
        self.current_command = self.state.current_command
        self.is_unix = self.state.is_unix
        self.scm_info = self.state.scm_info
        self.credentials = self.state.credentials
        self.in_assist_mode = in_assist_mode

    def run(self, stage_id):
        fn = self._get_stage_method(stage_id)
        assert fn, 'Unknown stage: %r' % stage_id
        command_list = fn()
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
            self.project_id, stage_id, python_path_list, in_assist_mode=self.in_assist_mode, **kw)

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
                StringProjectParameter('project_id', 'project_id to test', default_value='ci'),
                ]
        else:
            return []
