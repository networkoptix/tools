import logging
import sys
import concurrent.futures

from ..utils import datetime_local_now, timedelta_to_str
from .platform import create_platform
from .test_info import RunInfo
from .test_process import GTestProcess, CTestProcess

log = logging.getLogger(__name__)


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
        config_vars = self._read_current_config()
        self._clean_core_files()
        self._create_nx_ini_file()
        self._collect_test_processes(config_vars)
        self._run_info = RunInfo([str(test_process) for test_process in self._processes])
        self._run_pre_checks()

    def _read_current_config(self):
        assert self._config_path.is_file(), 'Current config file is required but is missing: %s' % self._config_path
        config_vars = {}
        execfile(str(self._config_path), config_vars)
        return config_vars

    def _clean_core_files(self):
        for path in self._work_dir.rglob('*.core.*'):
            log.info('Removing old core file %s', path)
            path.unlink()

    def _create_nx_ini_file(self):
        """Create nx_utils.ini file. For more details, please see:
            - https://networkoptix.atlassian.net/browse/CI-248
            - https://networkoptix.atlassian.net/wiki/spaces/SD/pages/83895081/Experimenting+and+debugging+.ini+files"""
        nx_ini_file = self._work_dir.joinpath('nx_utils.ini')
        nx_ini_file.open('w').writelines(
            [u'assertCrash=1\n', u'assertHeavyCondition=1'])

    def _collect_test_processes(self, config_vars):
        env = self._platform.env_with_library_path(config_vars)
        # Setup NX_INI_DIR
        # https://networkoptix.atlassian.net/wiki/spaces/SD/pages/83895081/Experimenting+and+debugging+.ini+files
        env['NX_INI_DIR'] = str(self._work_dir)
        for binary_name in self._binary_list:
            test_name = self._binary_to_test_name(binary_name)
            executable_path = self._bin_dir / binary_name
            find_test = False
            for test_binary_cls in [GTestProcess, CTestProcess]:
                if test_binary_cls.is_test_suite(executable_path, env):
                    self._processes += list(
                        test_binary_cls.get_test_processes(
                            self._platform, env, self._work_dir, test_name, executable_path))
                    find_test = True
                    break
            if not find_test:
                log.warning('Test executable file %s is not found', executable_path)

    def _run_pre_checks(self):
        error_list = self._platform.do_unittests_pre_checks()
        if not error_list:
            return
        for error in error_list:
            log.warning('Environment configuration error: %s', error)
        self._run_info.errors += error_list

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
                    # test_timeout should be used for google tests only
                    timeout = None
                    if isinstance(process, GTestProcess):
                        timeout = self._test_timeout.seconds
                    # Wait test finished or timed out
                    future.result(timeout=timeout)
                except concurrent.futures.TimeoutError:
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
