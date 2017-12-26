from ..utils import SimpleNamespace


class MatrixCell(object):

    def __init__(self):
        self.started_at = None
        self.build = None
        self.unit = None
        self.functional = None

    def add_run(self, run):
        # run.test.path is one of 'build', 'unit' or 'functional'
        if not getattr(self, run.test.path) or run.outcome != 'passed':
            # failed one must be preferred to be shown
            setattr(self, run.test.path, SimpleNamespace(run=run))
        if not self.started_at or run.started_at < self.started_at:
            self.started_at = run.started_at  # use earliest one

