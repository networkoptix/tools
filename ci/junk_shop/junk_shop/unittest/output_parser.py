from datetime import timedelta
from collections import deque
import logging

from collections import namedtuple
from ..google_test_parser import TestEventHandler, GTestParser


log = logging.getLogger(__name__)


ARTIFACT_LINE_COUNT_LIMIT = 100000
OUTPUT_ARTIFACT_NAME = 'output'
GTEST_ERROR_ARTIFACT_NAME = 'gtest errors'
PARSE_ERROR_ARTIFACT_NAME = 'parse errors'
ERROR_ARTIFACT_NAME = 'errors'
COMMAND_LINE_ARTIFACT_NAME = 'command line'
FULL_OUTPUT_ARTIFACT_NAME = 'full output'

# TODO: the entity looks unnecessary, will be removed later
TestArtifactsContainer = namedtuple('TestArtifactsContainer', ['test_info', 'output_file', 'backtrace_files'])


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


class BaseTestResultsStorage(object):
    """Base class to store test results"""

    def __init__(
            self, test_name, is_leaf, test_artifacts,
            started_at, duration, passed):
        assert test_artifacts is None or isinstance(test_artifacts, TestArtifactsContainer), repr(test_artifacts)
        self.test_name = test_name
        self.is_leaf = is_leaf
        self.test_artifacts = test_artifacts
        self.duration = duration
        self.started_at = started_at
        self.passed = passed
        self.lines_artifacts = {}  # name -> LinesArtifact
        self.output_lines = self._make_lines_artifact(OUTPUT_ARTIFACT_NAME)
        self.gtest_errors = self._make_lines_artifact(GTEST_ERROR_ARTIFACT_NAME, is_error=True)
        self.parse_errors = self._make_lines_artifact(PARSE_ERROR_ARTIFACT_NAME, is_error=True)
        self.errors = self._make_lines_artifact(ERROR_ARTIFACT_NAME, is_error=True)  # misc errors

    def _make_lines_artifact(self, name, is_error=False):
        self.lines_artifacts[name] = lines_artifact = LinesArtifact(name, is_error)
        return lines_artifact


class CTestResultsStorage(BaseTestResultsStorage):
    """C++ test results storage"""

    def __init__(
            self, test_name, is_leaf=False, test_artifacts=None,
            started_at=None, duration=None, passed=True):
        super(CTestResultsStorage, self).__init__(
            test_name, is_leaf, test_artifacts,
            started_at, duration, passed)
        self.children = []


class GTestResultsStorage(BaseTestResultsStorage):
    """Google test results storage"""

    def __init__(self, test_name, is_leaf=False, test_artifacts=None,
                 started_at=None, duration=None, passed=True):
        super(GTestResultsStorage, self).__init__(
            test_name, is_leaf, test_artifacts,
            started_at, duration, passed)
        self._children = {}

    @property
    def children(self):
        return self._children.values()

    def add_child(self, test_name, test_artifacts):
        test_started_at = test_artifacts.test_info.started_at
        test_passed = test_artifacts.test_info.exit_code == 0
        test_duration = test_artifacts.test_info.duration
        child = self
        for test_name in test_name.split('.'):
            child.duration += test_duration
            child.passed = child.passed and test_passed
            child.started_at = min(child.started_at, test_started_at)
            child = child._children.setdefault(
                test_name, GTestResultsStorage(
                    test_name,
                    started_at=test_started_at,
                    duration=test_duration,
                    passed=test_passed))
        child.test_artifacts = test_artifacts
        child.is_leaf = True
        return child


# TODO: CTest -> NxKitTest, so the parser might be changed
# TODO: https://networkoptix.atlassian.net/browse/CI-255
class CTestOutputParser(TestEventHandler):
    """Use `CTestOutputParser` to parse c++ test output file.
    We've decided that CTest output should be google test formatted,
    so we use `GTestParser` to parse their output.
    """

    @classmethod
    def run(cls, test_name, output_file, test_artifacts, is_aborted):
        parser = cls(test_name, test_artifacts)
        return parser.parse(output_file, is_aborted)

    def __init__(self, test_name, test_artifacts):
        self._levels = [
            CTestResultsStorage(
                test_name, test_artifacts=test_artifacts,
                started_at=test_artifacts.test_info.started_at,
                duration=test_artifacts.test_info.duration,
                passed=test_artifacts.test_info.exit_code == 0)
        ]  # [test binary, suite, test]

    def parse(self, output_file, is_aborted):
        parser = GTestParser(self)
        with output_file.open('rb') as f:
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
        results = CTestResultsStorage(test_name, is_leaf=is_leaf)
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


class GTestOutputParser(TestEventHandler):
    """Use `GTestCaseOutputParser` to parse google test case output file.
    Google test case - a google test run with `--gtest_filter` parameter for a single case.
    `GTestParser` is used to parse output (only one test case expected in output).
    """

    @classmethod
    def run(cls, output_file, test_results, is_aborted):
        parser = cls(test_results)
        return parser.parse(output_file, is_aborted)

    def __init__(self, test_results):
        self._test_results = test_results

    def parse(self, output_file, is_aborted):
        parser = GTestParser(self)
        with output_file.open('rb') as f:
            for line in iter(f.readline, ''):
                parser.process_line(line)
        parser.finish(is_aborted)
        return self._test_results

    def on_parse_error(self, error):
        self._test_results.parse_errors.add(error)

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
        # We always have valid status & duration for a google test case,
        # so we don't need to process it here
        pass
