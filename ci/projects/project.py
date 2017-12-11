import logging
import os.path
from command import UnstashCommand, CheckoutCommand, PythonStageCommand
from state import InputState, OutputState

log = logging.getLogger(__name__)


JUNK_SHOP_DIR = 'devtools/ci/junk_shop'


class JenkinsProject(object):

    def __init__(self, in_assist_mode):
        self.in_assist_mode = in_assist_mode

    def run(self, stage_id, input_state):
        fn = self._get_stage_method(stage_id)
        assert fn, 'Unknown stage: %r' % stage_id
        output_state = fn(input_state)
        assert output_state is None or isinstance(output_state, OutputState), (
            'Method %r must return OutputState instance, but returned: %r' % (method_name, output_state))
        return output_state or input_state.make_output_state()

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

