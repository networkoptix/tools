import logging
import shutil
from datetime import datetime, timedelta
from .platform import create_platform

log = logging.getLogger(__name__)

DUMP_FILE_CREATION_DELAY = timedelta(seconds=10)
TRACEBACK_SUFFIX = '.bt'


def collect_dump_file_list(test_name, test_info, dump_dir, test_dir_base):
    for path in dump_dir.glob('*{}.exe*.dmp'.format(test_name)):
        dump_time = datetime.utcfromtimestamp(path.stat().st_mtime)
        if test_info.started_at <= dump_time < test_info.started_at + test_info.duration + DUMP_FILE_CREATION_DELAY:
            test_dump_path = test_dir_base / path.name
            shutil.move(str(path), str(test_dump_path))
            log.info('Backtrace file for test %r: %s', test_name, test_dump_path)
            yield test_dump_path


def produce_dump_backtrace(binary_path, dump_file_path):
    platform = create_platform()
    backtrace = platform.extract_core_backtrace(binary_path, dump_file_path)
    backtrace_path = dump_file_path.with_suffix(TRACEBACK_SUFFIX)
    backtrace_path.write_bytes(backtrace)
    return backtrace_path
