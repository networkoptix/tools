from datetime import timedelta
from collections import deque
import logging

from collections import namedtuple
from ..google_test_parser import GoogleTestEventHandler, GoogleTestParser


log = logging.getLogger(__name__)


ARTIFACT_LINE_COUNT_LIMIT = 100000


TestArtifacts = namedtuple('TestArtifacts', 'test_info output_file_path backtrace_file_list')


def split_test_name(test_name):
    test_parts = test_name.split('.')
    return test_parts[0], '.'.join(test_parts[1:])


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


class BaseTestResults(object):
    """Base class to store test results"""

    def __init__(self, test_name, test_artifacts, is_leaf):
        assert test_artifacts is None or isinstance(test_artifacts, TestArtifacts), repr(test_artifacts)
        self.test_name = test_name
        self.is_leaf = is_leaf
        self.test_artifacts = test_artifacts
        self.duration = None
        self.started_at = None
        self.passed = True
        if self.test_artifacts:
            self.started_at = test_artifacts.test_info.started_at
            self.duration = test_artifacts.test_info.duration
            self.passed = (
                test_artifacts.test_info.exit_code == 0 and not test_artifacts.backtrace_file_list)
        self.lines_artifacts = {}  # name -> LinesArtifact
        self.output_lines = self._make_lines_artifact('output')
        self.gtest_errors = self._make_lines_artifact('gtest errors', is_error=True)
        self.parse_errors = self._make_lines_artifact('parse errors', is_error=True)
        self.errors = self._make_lines_artifact('errors', is_error=True)  # misc errors

    def _make_lines_artifact(self, name, is_error=False):
        self.lines_artifacts[name] = lines_artifact = LinesArtifact(name, is_error)
        return lines_artifact


class CTestResults(BaseTestResults):
    """C++ test results storage"""

    def __init__(self, test_name, test_artifacts=None, is_leaf=False):
        super(CTestResults, self).__init__(
            test_name, test_artifacts, is_leaf)
        self.children = []


class GTestResults(BaseTestResults):
    """Google test results storage"""

    def __init__(self, test_name, test_artifacts, is_leaf=False):
        super(GTestResults, self).__init__(
            test_name, test_artifacts, is_leaf)
        self._children = {}
        # To show artifacts in 'leaf' node only
        if not is_leaf:
            self.test_artifacts = None

    @property
    def children(self):
        return self._children.values()

    def add_children(self, test_name, test_artifacts):
        test_name, test_name_suffix = split_test_name(test_name)
        if not test_name_suffix:
            self._children[test_name] = child = GTestResults(
                test_name, test_artifacts=test_artifacts, is_leaf=True)
            return child
        child = self._children.setdefault(
            test_name, GTestResults(
                test_name, test_artifacts=test_artifacts)
        )
        self.duration += child.duration
        self.passed = self.passed and child.passed
        self.started_at = min(self.started_at, child.started_at)
        return child.add_children(test_name_suffix, test_artifacts)


#
class CTestOutputParser(GoogleTestEventHandler):
    """Use CTestParser to parse test output file (google test formatted).
    Implement GoogleTestEventHandler methods to construct TestResult tree.
    Return result tree root.C++ test output parser (expect output in google test format)
    """

    @classmethod
    def run(cls, test_name, test_artifacts, is_aborted):
        parser = cls(test_name, test_artifacts)
        return parser.parse(is_aborted)

    def __init__(self, test_name, test_artifacts):
        self._test_artifacts = test_artifacts
        self._levels = [
            CTestResults(test_name, test_artifacts=self._test_artifacts)
        ]  # [test binary, suite, test]

    def parse(self, is_aborted):
        parser = GoogleTestParser(self)
        with self._test_artifacts.output_file_path.open('rb') as f:
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
        results = CTestResults(test_name, is_leaf=is_leaf)
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


class GTestOutputParser(GoogleTestEventHandler):
    """Use GTestParser to parse google test output file (one test case per output).
    Implement GoogleTestEventHandler methods to construct TestResult tree.
    Return result tree root. test output parser (expect output in google test format)"""

    @classmethod
    def run(cls, test_results, is_aborted):
        parser = cls(test_results)
        return parser.parse(is_aborted)

    def __init__(self, test_results):
        self._test_results = test_results

    def parse(self, is_aborted):
        parser = GoogleTestParser(self)
        with self._test_results.test_artifacts.output_file_path.open('rb') as f:
            for line in iter(f.readline, ''):
                parser.process_line(line)
        parser.finish(is_aborted)
        return self._test_results

    def on_parse_error(self, error):
        self._test_results[0].parse_errors.add(error)

    def on_gtest_error(self, line):
        self._test_results.gtest_errors.add(line)

    def on_output_line(self, line):
        self._test_results.output_lines.add(line)

    def on_suite_start(self, suite_name):
        pass

    def on_suite_stop(self, duration_ms):
        pass

    def on_test_start(self, test_name):
        pass

    def on_test_stop(self, status, duration_ms, is_aborted=False):
        if is_aborted:
            self._test_results.errors.add('aborted')
