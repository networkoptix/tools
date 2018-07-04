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
    print('Making backtraces from core files from %s:' % work_dir)
    for test_name in run_info.test_list:
        make_test_backtraces(work_dir, test_name)
    print('Done.')


def make_test_backtraces(work_dir, test_name):
    """Create backtrace files unittests in the `work_dir` for the test by `test_name`"""
    platform = create_platform()
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    for core_file_path in platform.collect_core_file_list(test_name, test_info, test_dir_base):
        produce_core_backtrace(platform, test_info.binary_path, core_file_path)


def produce_core_backtrace(platform, binary_path, core_file_path):
    """Extract backtrace from crash file `core_file_path` for `platform`.
    `binary_path` is using as executable and symbol path"""
    detected_binary_path = platform.extract_core_source_binary(str(core_file_path))
    if detected_binary_path and detected_binary_path.is_file():
        # extract_core_source_binary may fail, returning None; use binary we known of then
        binary_path = detected_binary_path
    backtrace = platform.extract_core_backtrace(binary_path, core_file_path)
    backtrace_path = core_file_path.with_suffix(core_file_path.suffix + TRACEBACK_SUFFIX)
    backtrace_path.write_bytes(backtrace)
    return backtrace_path


def collect_backtrace_file_list(test_name, test_work_dir):
    """Collect crash files for test by `test_name`.
    `test_work_dir` is using to get prerequisites and store artifacts."""
    for path in test_work_dir.rglob(TRACEBACK_PATTERN):
        log.info('Backtrace file for test %r: %s', test_name, path)
        yield path
