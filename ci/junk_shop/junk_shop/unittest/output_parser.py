from datetime import timedelta
from collections import deque
import logging

from ..google_test_parser import GoogleTestEventHandler, GoogleTestParser


log = logging.getLogger(__name__)


ARTIFACT_LINE_COUNT_LIMIT = 100000


class LinesArtifact(object):

    def __init__(self, name, is_error=False):
        self.name = name
        self.is_error = is_error
        self.is_truncated = False
        self.line_count = 0
        self.line_count_limit = ARTIFACT_LINE_COUNT_LIMIT
        self._line_list = deque(maxlen=self.line_count_limit)

    def add(self, line):
        if len(self._line_list) >= self.line_count_limit:
            self.is_truncated = True
        self._line_list.append(line)
        self.line_count += 1

    @property
    def data(self):
        return '\n'.join(self._line_list)


class TestResults(object):

    def __init__(self, test_name, is_leaf=False):
        self.test_name = test_name
        self.is_leaf = is_leaf
        self.passed = True
        self.duration = None
        self.lines_artifacts = {}  # name -> LinesArtifact
        self.output_lines = self._make_lines_artifact('output')
        self.gtest_errors = self._make_lines_artifact(
            'gtest errors', is_error=True)
        self.parse_errors = self._make_lines_artifact(
            'parse errors', is_error=True)
        self.errors = self._make_lines_artifact(
            'errors', is_error=True)  # misc errors
        self.children = []

    def _make_lines_artifact(self, name, is_error=False):
        self.lines_artifacts[name] = lines_artifact = LinesArtifact(
            name, is_error)
        return lines_artifact


# Use GoogleTestParser to parse google test output file.
# Implement GoogleTestEventHandler methods to construct TestResult tree.
# Return result tree root.
class GTestOutputParser(GoogleTestEventHandler):

    @classmethod
    def run(cls, test_name, output_file_path, is_aborted):
        parser = cls(test_name)
        return parser.parse(output_file_path, is_aborted)

    def __init__(self, test_name):
        self._levels = [TestResults(test_name)]  # [test binary, suite, test]

    def parse(self, output_file_path, is_aborted):
        parser = GoogleTestParser(self)
        with output_file_path.open('rb') as f:
            for line in iter(f.readline, ''):
                parser.process_line(line)
        parser.finish(is_aborted)
        if not self._levels:
            return None
        if len(self._levels) > 1 and not is_aborted:
            self._levels[0].parse_errors.add('Unexpected end of test output')
        return self._levels[0]

    def on_parse_error(self, error):
        if self._levels:
            self._levels[0].parse_errors.add(error)
        else:
            log.warning('parse error: %s', error)

    def on_gtest_error(self, line):
        self._levels[-1].gtest_errors.add(line)

    def on_output_line(self, line):
        self._levels[-1].output_lines.add(line)

    def on_suite_start(self, suite_name):
        self._add_level(suite_name, is_leaf=False)

    def on_suite_stop(self, duration_ms):
        assert len(self._levels) == 2, len(self._levels)
        self._drop_level(duration_ms)

    def on_test_start(self, test_name):
        self._add_level(test_name, is_leaf=True)

    def on_test_stop(self, status, duration_ms, is_aborted=False):
        assert len(self._levels) == 3, len(self._levels)
        if is_aborted:
            status = 'FAILED'
            self._levels[-1].errors.add('aborted')
        self._drop_level(duration_ms, status)

    def _add_level(self, test_name, is_leaf):
        results = TestResults(test_name, is_leaf)
        self._levels[-1].children.append(results)
        self._levels.append(results)

    def _drop_level(self, duration_ms, status=None):
        level = self._levels.pop()
        if status is not None:
            level.passed = status == 'OK'
        if duration_ms is not None:
            level.duration = timedelta(milliseconds=int(duration_ms))
        if not level.passed:
            self._levels[-1].passed = False
