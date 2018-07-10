"""
junk_shop.unittest.make_backtraces
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Helpers to make backtraces from posix core-files and windows dump-files
"""
import logging

from .test_info import RunInfo, TestInfo
from .platform import create_platform, TRACEBACK_SUFFIX


TRACEBACK_PATTERN = '*' + TRACEBACK_SUFFIX


log = logging.getLogger(__name__)


def make_backtraces(work_dir):
    """Create backtrace files for unittests in the `work_dir`"""
    run_info = RunInfo.load_from_dir(work_dir)
    log.info('Making backtraces from core files from %s:' % work_dir)
    for test_name in run_info.test_list:
        _make_test_backtraces(work_dir, test_name)
    log.info('Done.')


def _make_test_backtraces(work_dir, test_name):
    """Create backtrace files unittests in the `work_dir` for the test by
    `test_name`"""
    platform = create_platform()
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    for core_file_path in platform.collect_core_file_list(test_name, test_info,
                                                          test_dir_base):
        platform.produce_core_backtrace(test_info.binary_path, core_file_path)


def collect_backtrace_file_list(test_name, test_work_dir):
    """Collect crash files for test by `test_name`.
    `test_work_dir` is using to get prerequisites and store artifacts."""
    for path in test_work_dir.rglob(TRACEBACK_PATTERN):
        log.info('Backtrace file for test %r: %s', test_name, path)
        yield path
