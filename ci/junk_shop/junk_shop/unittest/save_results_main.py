import logging
import argparse
from collections import namedtuple

from pathlib2 import Path

from junk_shop.utils import DbConfig
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
from .test_info import RunInfo, TestInfo
from .output_parser import GTestOutputParser
from .core_file import collect_core_file_list, produce_core_traceback
from .save_results import save_test_results

log = logging.getLogger(__name__)


TestRecord = namedtuple('TestRecord', 'test_name test_info output_file_path test_results core_file_list backtrace_file_list')


def parse_and_save_results_to_db(work_dir, repository):
    run_info = RunInfo.load_from_dir(work_dir)
    print 'Parsing unit test results from %s:' % work_dir
    test_record_list = [produce_test_record(work_dir, test_name) for test_name in run_info.test_list]
    print 'Saving unit test results:'
    passed = save_test_results(repository, test_record_list)
    print 'Done.'
    return passed

def produce_test_record(work_dir, test_name):
    test_dir_base = work_dir.joinpath(test_name)
    test_info = TestInfo.load_from_file(test_dir_base.with_suffix('.yaml'))
    output_file_path = test_dir_base.with_suffix('.output')
    test_results = GTestOutputParser.run(test_name, output_file_path)
    core_file_list = list(collect_core_file_list(test_name, test_dir_base))
    backtrace_file_list = [produce_core_traceback(test_info.binary_path, core_file_path)
                               for core_file_path in core_file_list]
    return TestRecord(test_name, test_info, output_file_path, test_results, core_file_list, backtrace_file_list)


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters')
    args = parser.parse_args()
    work_dir = Path.cwd()
    repository = DbCaptureRepository(args.db_config, args.build_parameters)
    setup_logging()
    is_passed = parse_and_save_results_to_db(work_dir, repository)
    if not is_passed:
        sys.exit(1)
