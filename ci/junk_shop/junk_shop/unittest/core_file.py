import logging

from .platform import create_platform

log = logging.getLogger(__name__)


def collect_core_file_list(test_name, test_work_dir):
    for path in test_work_dir.rglob('*.core.*'):
        if path.suffix == '.bt':
            continue  # skip backtraces generated from these cores
        log.info('Core file is left after %r: %s', test_name, path)
        yield path

def produce_core_traceback(binary_path, core_file_path):
    platform = create_platform()
    detected_binary_path = platform.extract_core_source_binary(str(core_file_path))
    if detected_binary_path and detected_binary_path.is_file():
        # extract_core_source_binary may fail, returning None; use binary we known of then
        binary_path = detected_binary_path
    backtrace = platform.extract_core_backtrace(binary_path, core_file_path)
    backtrace_path = core_file_path.with_suffix(''.join(core_file_path.suffixes + ['.bt']))
    backtrace_path.write_bytes(backtrace)
    return backtrace_path
