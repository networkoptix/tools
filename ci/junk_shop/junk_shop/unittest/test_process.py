#!/usr/bin/env python

# run unit tests, store results to a directory: yaml+log+core tracebacks

import logging
import subprocess
import time

from ..utils import datetime_local_now
from .test_info import TestInfo

log = logging.getLogger(__name__)


POPEN_BUF_SIZE = 10*1024  # 10K
DEFAULT_LOG_LEVEL = 'DEBUG1'

TEST_LOG_LEVEL = dict(
    nx_network_ut='DEBUG2',
    cloud_connectivity_ut='DEBUG2',
    traffic_relay_ut='DEBUG2',
    connection_mediator_ut='DEBUG2',
    cloud_db_ut='DEBUG2',
    relaying_ut='DEBUG2',
    vms_gateway_ut='DEBUG2',
    )


class SimpleTestProcess(object):

    def __init__(self, platform, config_vars, root_work_dir, test_name, executable_path):
        self._config_vars = config_vars
        self._root_work_dir = root_work_dir  # pathlib2.Path
        self._platform = platform
        self._test_name = test_name  # aka executable file name
        self._executable_path = executable_path  # full path to test binary, *_ut, pathlib2.Path
        self._pipe = None
        self._test_info = TestInfo(executable_path)
        self._output_file = None
        if not self.work_dir.is_dir():
            log.info('Creating test working directory: %s', self.work_dir)
            self.work_dir.mkdir(parents=True)
            # Prepare nx_utils.ini file
            # For more details, please see:
            #  - https://networkoptix.atlassian.net/browse/CI-248
            #  - https://networkoptix.atlassian.net/wiki/spaces/SD/pages/83895081/Experimenting+and+debugging+.ini+files
            nx_ini_file = self.work_dir.joinpath('nx_utils.ini')
            nx_ini_file.open('w').write(
                u'assertCrash=1\nassertHeavyCondition=1')

    @property
    def work_dir(self):
        return self._root_work_dir / self._test_name

    def __str__(self):
        return '%s' % self._test_name

    def get_arguments(self):
        return []

    def __call__(self):
        env = self._platform.env_with_library_path(self._config_vars)
        env['NX_INI_DIR'] = str(self.work_dir)
        args = [str(self._executable_path),
                '--tmp=%s' % self.work_dir] + self.get_arguments()
        self._test_info.command_line = subprocess.list2cmdline(args)
        if not self._executable_path.exists():
            self._test_info.errors.append('Test executable is missing: %r' % self._executable_path)
            return
        output_file_path = self._root_work_dir.joinpath(str(self) + '.output')
        self._output_file = output_file_path.open('wb')

        try:
            log.debug('Start %s', args)
            self._pipe = subprocess.Popen(
                args,
                cwd=str(self.work_dir),
                env=env,
                stdout=self._output_file,
                stderr=subprocess.STDOUT,
                bufsize=POPEN_BUF_SIZE,
                )
        except OSError as x:
            log.info('%s failed on start', self)
            log.exception(x)
            self._test_info.errors.append('Error starting %r: %s' % (self._executable_path, x))
            return
        self._test_info.started_at = datetime_local_now()
        log.info('%s is started', self)
        while not self.is_finished():
            time.sleep(1)
        self._close()

    def _close(self):
        if self._output_file:
            self._output_file.close()
        if self._pipe:
            self._test_info.exit_code = self._pipe.wait()
        self._test_info.duration = datetime_local_now() - self._test_info.started_at
        if self._test_info.timed_out:
            self._test_info.errors.append(
                'Aborted by timeout, still running after %s seconds' % self._test_info.duration.total_seconds())

        self._test_info.save_to_file(
            self._root_work_dir.joinpath(str(self) + '.yaml'))

        log.info('%s ended with exit code %d', self, self._test_info.exit_code)

    def abort(self):
        if self.is_finished():
            return
        log.warning('%s is aborted', self)
        self._test_info.timed_out = True
        self._platform.abort_process(self._pipe)
        self._pipe.wait()

    def is_finished(self):
        if not self._pipe:
            return True
        return self._pipe.poll() is not None

    def process_core_files(self):
        for core_file_path in self._platform.collect_core_file_list(
                self._test_name, self._test_info, self.work_dir):
            self._platform.produce_core_backtrace(
                self._test_info.binary_path, core_file_path)


class GoogleTestProcess(SimpleTestProcess):

    def __init__(self, platform, config_vars, root_work_dir, test_name, test_case_name, executable_path):
        self._test_case_name = test_case_name
        super(GoogleTestProcess, self).__init__(
            platform, config_vars, root_work_dir, test_name, executable_path)

    @property
    def work_dir(self):
        return self._root_work_dir / self._test_name / self._test_case_name

    def __str__(self):
        return '%s.%s' % (self._test_name, self._test_case_name)

    def get_arguments(self):
        log_level = TEST_LOG_LEVEL.get(self._test_name, DEFAULT_LOG_LEVEL)
        # developers asked for these flags to be used for unit tests
        return [
            '--gtest_filter=%s' % self._test_case_name,
            '--log-level=%s' % log_level,
        ]
