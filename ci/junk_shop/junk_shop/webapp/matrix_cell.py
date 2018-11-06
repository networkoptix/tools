from ..utils import SimpleNamespace
from .utils import STAGE_NAMES
from collections import OrderedDict


class MatrixCell(object):

    def __init__(self):
        self.started_at = None
        self.stages = OrderedDict([(stage, None) for stage in STAGE_NAMES])

    def add_run(self, run):
        # run.test.path is one of 'build', 'unit' or 'functional'
        last_run = self.stages.get(run.test.path)
        if not last_run or run.started_at > last_run.run.started_at:
            # failed one must be preferred to be shown
            self.stages[run.test.path] = SimpleNamespace(run=run)
        if not self.started_at or run.started_at < self.started_at:
            self.started_at = run.started_at  # use earliest one
