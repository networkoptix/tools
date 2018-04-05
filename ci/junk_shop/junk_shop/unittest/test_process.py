#!/usr/bin/env python

# run unit tests, store results to a directory: yaml+log+core tracebacks

import logging
import subprocess

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


def gtest_arguments(test_name):
    log_level = TEST_LOG_LEVEL.get(test_name, DEFAULT_LOG_LEVEL)
    # developers asked for these flags to be used for unit tests
    return [
        '--gtest_filter=-NxCritical.All3',
        '--gtest_shuffle',
        '--log-level=%s' % log_level,
        ]


class TestProcess(object):

    def __init__(self, platform, config_vars, root_work_dir, test_name, binary_path):
        self._config_vars = config_vars
        self._root_work_dir = root_work_dir  # pathlib2.Path
        self._work_dir = root_work_dir / test_name
        self._platform = platform
        self._test_name = test_name  # aka executable file name
        self._binary_path = binary_path  # full path to test binary, *_ut, pathlib2.Path
        self._pipe = None
        self._test_info = TestInfo(binary_path)
        self._output_file = None
        if not self._work_dir.is_dir():
            log.info('Creating test working directory: %s', self._work_dir)
            self._work_dir.mkdir(parents=True)

    def start(self):
        env = self._platform.env_with_library_path(self._config_vars)
        args = [
            str(self._binary_path),
            '--tmp=%s' % self._work_dir,
            ] + gtest_arguments(self._test_name)
        self._test_info.command_line = subprocess.list2cmdline(args)
        if not self._binary_path.exists():
            self._test_info.errors.append('Test executable is missing: %r' % self._binary_path)
            return
        output_file_path = self._root_work_dir.joinpath(self._test_name).with_suffix('.output')
        self._output_file = output_file_path.open('wb')
        try:
            self._pipe = subprocess.Popen(
                args,
                cwd=str(self._work_dir),
                env=env,
                stdout=self._output_file,
                stderr=subprocess.STDOUT,
                bufsize=POPEN_BUF_SIZE,
                )
        except OSError as x:
            self._test_info.errors.append('Error starting %r: %s' % (self._binary_path, x))
            return
        self._test_info.started_at = datetime_local_now()
        log.info('%s is started', self._test_name)

    def is_finished(self):
        if not self._pipe: return True
        return self._pipe.poll() is not None

    def abort(self, run_duration):
        if self.is_finished():
            return
        log.warning('Aborting %s', self._test_name)
        self._test_info.errors.append(
                'Aborted by timeout, still running after %s seconds' % run_duration.total_seconds())
        self._test_info.timed_out = True
        self._platform.abort_process(self._pipe)
        self._pipe.wait()

    def close(self):
        if not self._pipe: return False
        if self._output_file:
            self._output_file.close()
        self._test_info.exit_code = exit_code = self._pipe.wait()
        self._test_info.duration = datetime_local_now() - self._test_info.started_at
        self._test_info.save_to_file(
            self._root_work_dir.joinpath(self._test_name).with_suffix('.yaml'))
        log.info('%s ended with exit code %d', self._test_name, exit_code)
