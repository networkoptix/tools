import logging
import argparse
from pathlib2 import Path
from .test_info import RunInfo, TestInfo
from .core_file import collect_core_file_list, produce_core_backtrace

log = logging.getLogger(__name__)


def make_backtraces(work_dir):
    run_info = RunInfo.load_from_dir(work_dir)
    print 'Making backtraces from core files from %s:' % work_dir
    for test_name in run_info.test_list:
        make_test_backtraces(work_dir, test_name)
    print 'Done.'

def make_test_backtraces(work_dir, test_name):
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    core_file_list = list(collect_core_file_list(test_name, test_dir_base))
    for core_file_path in core_file_list:
        produce_core_backtrace(test_info.binary_path, core_file_path)


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def main():
    work_dir = Path.cwd()
    setup_logging()
    make_backtraces(work_dir)
