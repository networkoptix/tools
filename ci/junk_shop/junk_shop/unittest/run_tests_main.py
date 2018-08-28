import logging
from datetime import timedelta
import argparse

from pathlib2 import Path

from ..utils import str_to_timedelta
from .test_runner import TestRunner

log = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 10
DEFAULT_TEST_TIMEOUT = "100s"  # 100 seconds


def run_unit_tests(config_path, work_dir, bin_dir, test_binary_list, timeout, max_workers, test_timeout):
    assert timeout is None or isinstance(timeout, timedelta), repr(timeout)
    runner = TestRunner(
        config_path, work_dir, bin_dir, test_binary_list, timeout, max_workers, test_timeout)
    try:
        runner.run()
    except Exception as x:
        runner.add_error('Internal unittest.py error: %r' % x)
        raise
    finally:
        runner.finalize()


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def dir_path(value):
    path = Path(value).expanduser()
    if not path.is_dir():
        raise argparse.ArgumentTypeError('%s is not an existing directory' % path)
    return path


def file_path(value):
    path = Path(value).expanduser()
    if not path.is_file():
        raise argparse.ArgumentTypeError('%s is not an existing file' % path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--timeout', type=str_to_timedelta, dest='timeout', help='Total run timeout, in format: 1d2h3m4s')
    parser.add_argument(
        '--max-workers', type=int, default=DEFAULT_MAX_WORKERS,
        help="Max. number of multiple tests to perform at a time, default={}.".format(DEFAULT_MAX_WORKERS))
    parser.add_argument(
        '--test-timeout', type=str_to_timedelta, default=DEFAULT_TEST_TIMEOUT,
        help="Test timeout, in format 1d2h3m4s, default={}.".format(DEFAULT_TEST_TIMEOUT))
    parser.add_argument('config_path', type=file_path, help='Path to current_config.py')
    parser.add_argument('bin_dir', type=dir_path, help='Directory to test binaries')
    parser.add_argument('test_binary', nargs='+', help='Executable for unit test, *_ut')
    args = parser.parse_args()
    work_dir = Path.cwd()
    setup_logging()
    run_unit_tests(
        args.config_path, work_dir, args.bin_dir, args.test_binary, args.timeout,
        args.max_workers, args.test_timeout)
