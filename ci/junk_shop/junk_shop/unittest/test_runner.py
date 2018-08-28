import logging
import sys
import subprocess
import concurrent.futures
import time

from ..utils import datetime_local_now, timedelta_to_str
from .platform import create_platform
from .test_info import RunInfo
from .test_process import SimpleTestProcess, GoogleTestProcess

log = logging.getLogger(__name__)


class SimpleTestBinary(object):

    @classmethod
    def is_test_suite(cls, executable_path):
        return True

    def get_test_processes(self, platform, config_vars, work_dir, test_name, executable_path):
        return [SimpleTestProcess(
            platform, config_vars, work_dir, test_name, executable_path)]


class GoogleTestBinary(object):

    @classmethod
    def is_test_suite(cls, executable_path):
        try:
            output = subprocess.check_output(
                [str(executable_path), '--help'],
                stderr=subprocess.STDOUT,
                universal_newlines=True)
        except (subprocess.CalledProcessError, OSError):
            return False
        else:
            return '--gtest_list_tests' in output

    def get_test_processes(self, platform, config_vars, work_dir, test_name, executable_path):
        output = subprocess.check_output([
            str(executable_path),
            '--gtest_list_tests',
            '--gtest_filter=-NxCritical.All3'],
            stderr=subprocess.STDOUT, universal_newlines=True)

        def strip_comment(x):
            comment_start = x.find('#')
            if comment_start != -1:
                x = x[:comment_start]
            return x

        for line in output.splitlines():
            has_indent = line.startswith(' ')
            if not has_indent and '.' in line:
                test_suite = strip_comment(line).strip()
            elif has_indent:
                test_case_name = test_suite + strip_comment(line).strip()
                yield GoogleTestProcess(
                        platform, config_vars, work_dir, test_name,
                        test_case_name.replace('/', '_'), executable_path)


class TestRunner(object):

    def __init__(
            self, config_path, work_dir, bin_dir, binary_list, timeout,
            max_workers, test_timeout):
        self._config_path = config_path
        self._work_dir = work_dir
        self._bin_dir = bin_dir
        self._binary_list = binary_list
        self._timeout = timeout  # timedelta
        self._platform = create_platform()
        self._max_workers = max_workers
        self._test_timeout = test_timeout  # timedelta
        self._processes = []
        self._prepare_test_env()

    def _prepare_test_env(self):
        self._run_pre_checks()
        config_vars = self._read_current_config()
        self._clean_core_files()
        self._collect_test_processes(config_vars)
        self._run_info = RunInfo([str(test_process) for test_process in self._processes])

    def _run_pre_checks(self):
        error_list = self._platform.do_unittests_pre_checks()
        if not error_list:
            return
        for error in error_list:
            log.warning('Environment configuration error: %s', error)
        self._run_info.errors += error_list

    def _clean_core_files(self):
        for path in self._work_dir.rglob('*.core.*'):
            log.info('Removing old core file %s', path)
            path.unlink()

    def _collect_test_processes(self, config_vars):
        for binary_name in self._binary_list:
            test_name = self._binary_to_test_name(binary_name)
            executable_path = self._bin_dir / binary_name
            for test_binary_cls in [GoogleTestBinary, SimpleTestBinary]:
                if test_binary_cls.is_test_suite(executable_path):
                    self._processes += list(
                        test_binary_cls().get_test_processes(
                            self._platform, config_vars, self._work_dir, test_name, executable_path))
                    break

    def _read_current_config(self):
        assert self._config_path.is_file(), 'Current config file is required but is missing: %s' % self._config_path
        config_vars = {}
        execfile(str(self._config_path), config_vars)
        return config_vars

    def run(self):
        self._run_info.started_at = datetime_local_now()
        aborted = False
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            for process, future in [(p, executor.submit(p)) for p in self._processes]:
                try:
                    # Check total run timeout
                    run_duration = datetime_local_now() - self._run_info.started_at
                    if self._timeout and run_duration > self._timeout:
                        process.abort()
                        if not aborted:
                            error = 'Timed out after %s; aborted' % timedelta_to_str(run_duration)
                            log.warning(error)
                            self._run_info.errors.append(error)
                            aborted = True
                    # Wait test finished or timed out
                    future.result(timeout=self._test_timeout.seconds)
                except concurrent.futures.TimeoutError:
                    if not process.is_finished():
                        process.abort()
                finally:
                    process.process_core_files()

    @staticmethod
    def _binary_to_test_name(binary_name):
        if sys.platform == 'win32' and binary_name.endswith('.exe'):
            return binary_name[:-len('.exe')]
        else:
            return binary_name

    def finalize(self):
        self._run_info.duration = datetime_local_now() - self._run_info.started_at
        self._run_info.save_to_dir(self._work_dir)

    def add_error(self, error):
        self._run_info.errors.append(error)
