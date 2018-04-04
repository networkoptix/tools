import logging
import sys
import time

from ..utils import datetime_local_now, timedelta_to_str
from .platform import create_platform
from .test_info import RunInfo
from .test_process import TestProcess

log = logging.getLogger(__name__)


class TestRunner(object):

    def __init__(self, config_path, work_dir, bin_dir, binary_list, timeout):
        self._config_path = config_path
        self._work_dir = work_dir
        self._bin_dir = bin_dir
        self._binary_list = binary_list
        self._timeout = timeout  # timedelta
        self._run_info = RunInfo([self._binary_to_test_name(binary_name) for binary_name in binary_list])
        self._platform = create_platform()

    def start(self):
        self._run_info.started_at = datetime_local_now()
        self._run_pre_checks()
        config_vars = self._read_current_config()
        self._clean_core_files()
        self._processes = [self._create_test_process(config_vars, binary_name) for binary_name in self._binary_list]
        for process in self._processes:
            process.start()

    def _run_pre_checks(self):
        error_list = self._platform.do_unittests_pre_checks()
        if not error_list: return
        for error in error_list:
            log.warning('Environment configuration error: %s', error)
        self._run_info.errors += error_list

    def _read_current_config(self):
        assert self._config_path.is_file(), 'Current config file is required but is missing: %s' % self._config_path
        config_vars = {}
        execfile(str(self._config_path), config_vars)
        return config_vars

    def _create_test_process(self, config_vars, binary_name):
        test_name = self._binary_to_test_name(binary_name)
        executable_path = self._bin_dir / binary_name
        return TestProcess(self._platform, config_vars, self._work_dir, test_name, executable_path)

    @staticmethod
    def _binary_to_test_name(binary_name):
        if sys.platform == 'win32' and binary_name.endswith('.exe'):
            return binary_name[:-len('.exe')]
        else:
            return binary_name

    def wait(self):
        aborted = False
        while self._processes:
            run_duration = datetime_local_now() - self._run_info.started_at
            if not aborted and self._timeout and run_duration > self._timeout:
                self._abort_processes(run_duration)
                aborted = True
            for process in self._processes[:]:
                if not process.is_finished(): continue
                process.close()
                self._processes.remove(process)
            time.sleep(1)

    def _abort_processes(self, run_duration):
        error = 'Timed out after %s seconds; aborted' % timedelta_to_str(run_duration)
        log.warning(error)
        self._run_info.errors.append(error)
        for process in self._processes:
            process.abort(run_duration)

    def finalize(self):
        self._run_info.duration = datetime_local_now() - self._run_info.started_at
        self._run_info.save_to_dir(self._work_dir)

    def add_error(self, error):
        self._run_info.errors.append(error)

    def _clean_core_files(self):
        for path in self._work_dir.rglob('*.core.*'):
            log.info('Removing old core file %s', path)
            path.unlink()
