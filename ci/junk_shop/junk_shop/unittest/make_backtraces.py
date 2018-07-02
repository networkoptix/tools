import logging
import os
from pathlib2 import Path
from .test_info import RunInfo, TestInfo
from .core_file import collect_core_file_list, produce_core_backtrace
from .windows_dump_file import collect_dump_file_list, produce_dump_backtrace

log = logging.getLogger(__name__)


def make_backtraces(work_dir, is_windows):
    run_info = RunInfo.load_from_dir(work_dir)
    print('Making backtraces from core files from %s:' % work_dir)
    for test_name in run_info.test_list:
        if is_windows:
            make_windows_test_backtraces(work_dir, test_name)
        else:
            make_test_backtraces(work_dir, test_name)
    print('Done.')


def make_test_backtraces(work_dir, test_name):
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    core_file_list = list(collect_core_file_list(test_name, test_dir_base))
    for core_file_path in core_file_list:
        produce_core_backtrace(test_info.binary_path, core_file_path)


def make_windows_test_backtraces(work_dir, test_name):
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    dump_dir = Path(os.environ['LOCALAPPDATA'])
    dump_file_list = list(collect_dump_file_list(test_name, test_info, dump_dir, test_dir_base))
    for dump_file_path in dump_file_list:
        produce_dump_backtrace(test_info.binary_path, dump_file_path)
