import logging
import argparse
import time
from collections import namedtuple

from pathlib2 import Path

from junk_shop.utils import DbConfig
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
from .test_info import RunInfo, TestInfo
from .output_parser import CTestOutputParser, GTestOutputParser, GTestResults, split_test_name, TestArtifacts
from .make_backtraces import collect_backtrace_file_list
from .save_results import save_test_results

log = logging.getLogger(__name__)


DEFAULT_UNIT_TEST_NAME = 'unit'


TestRecord = namedtuple('TestRecord', 'test_name test_results')


def parse_and_save_results_to_db(work_dir, repository, root_name=DEFAULT_UNIT_TEST_NAME):
    run_info = RunInfo.load_from_dir(work_dir)
    log.info('Parsing unit test results from %s:', work_dir)
    test_record_list = get_test_record_list(work_dir, run_info)
    log.info('Saving unit test results:')
    t = time.time()
    passed = save_test_results(repository, root_name, run_info, test_record_list)
    log.info('Done in %r seconds.' % (time.time() - t))
    return passed


def get_test_record_list(work_dir, run_info):
    test_records = dict()
    for test_name in run_info.test_list:
        binary_name, test_case_name = split_test_name(test_name)
        test_info = TestInfo.load_from_file(work_dir.joinpath(test_name + '.yaml'))
        output_file_path = work_dir.joinpath(test_name + '.output')
        killed_by_signal = test_info.exit_code < 0
        is_aborted = test_info.timed_out or killed_by_signal

        dump_dir = work_dir / binary_name / test_case_name
        backtrace_file_list = list(collect_backtrace_file_list(binary_name, dump_dir))
        test_artifacts = TestArtifacts(test_info, output_file_path, backtrace_file_list)
        is_gtest = bool(test_case_name)
        if is_gtest:
            test_record = test_records.setdefault(
                binary_name,
                TestRecord(binary_name, GTestResults(binary_name, test_artifacts)))
            test_results = test_record.test_results.add_children(
                test_case_name, test_artifacts)
            GTestOutputParser.run(test_results, is_aborted)
        else:
            test_results = CTestOutputParser.run(test_name, test_artifacts, is_aborted)
            test_records[test_name] = TestRecord(test_name, test_results)
    return test_records.values()


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('build_parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters')
    parser.add_argument('--test-name', default=DEFAULT_UNIT_TEST_NAME,
                        help='Name of tests, default is %r' % DEFAULT_UNIT_TEST_NAME)
    args = parser.parse_args()
    work_dir = Path.cwd()
    repository = DbCaptureRepository(args.db_config, args.build_parameters)
    setup_logging()
    parse_and_save_results_to_db(work_dir, repository, args.test_name)
