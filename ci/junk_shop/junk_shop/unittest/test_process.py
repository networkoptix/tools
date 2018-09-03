#!/usr/bin/env python

# run unit tests, store results to a directory: yaml+log+core tracebacks

import logging
import subprocess
import time
import abc

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


class BaseTestProcess(object):
    """The base abstract class to run test binary file"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, platform, env, root_work_dir, test_name, executable_path):
        self._env = env
        self._root_work_dir = root_work_dir  # pathlib2.Path
        self._platform = platform
        self._test_name = test_name  # aka executable file name
        self._executable_path = executable_path  # full path to test binary, *_ut, pathlib2.Path
        self._pipe = None
        self._test_info = TestInfo(executable_path)
        self._output_file = None
        if not self.work_dir.is_dir():
            log.debug('Creating test working directory: %s', self.work_dir)
            self.work_dir.mkdir(parents=True)

    @property
    @abc.abstractmethod
    def work_dir(self):
        pass

    @classmethod
    @abc.abstractmethod
    def is_test_suite(cls, executable_path, env):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_test_processes(cls, platform, env, work_dir, test_name, executable_path):
        raise NotImplementedError

    def get_arguments(self):
        return []

    def __call__(self):
        try:
            self._test_info.started_at = datetime_local_now()
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
                    env=self._env,
                    stdout=self._output_file,
                    stderr=subprocess.STDOUT,
                    bufsize=POPEN_BUF_SIZE,
                )
            except OSError as x:
                log.info('%s failed on start', self)
                log.exception(x)
                self._test_info.errors.append('Error starting %r: %s' % (self._executable_path, x))
                # It's fake exit code to mark test as failed
                self._test_info.exit_code = -1
                return
            log.info('%s is started', self)
            while not self.is_finished():
                time.sleep(1)
        finally:
            self._close()

    def _close(self):
        if self._output_file:
            self._output_file.close()
        if self._pipe:
            self._test_info.exit_code = self._pipe.wait()
        if self._test_info.started_at:
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
        """Collect & make backtraces from crash files if test process is failed."""
        if self._test_info.exit_code != 0:
            for core_file_path in self._platform.collect_core_file_list(
                self._test_name, self._test_info, self.work_dir):
                self._platform.produce_core_backtrace(
                    self._test_info.binary_path, core_file_path)


class CTestProcess(BaseTestProcess):
    """Nx_vms C++ test process"""

    def __init__(self, platform, env, root_work_dir, test_name, executable_path):
        super(CTestProcess, self).__init__(
            platform, env, root_work_dir, test_name, executable_path)

    def __str__(self):
        return '%s' % self._test_name

    @property
    def work_dir(self):
        return self._root_work_dir / self._test_name

    @classmethod
    def is_test_suite(cls, executable_path, env):
        return executable_path.exists()

    @classmethod
    def get_test_processes(cls, platform, env, work_dir, test_name, executable_path):
        return [cls(
            platform, env, work_dir, test_name, executable_path)]


class GTestProcess(BaseTestProcess):
    """Nx_vms google test process"""

    def __init__(self, platform, env, root_work_dir, test_name, test_case_name, executable_path):
        self._test_case_name = test_case_name
        super(GTestProcess, self).__init__(
            platform, env, root_work_dir, test_name, executable_path)

    @property
    def work_dir(self):
        return self._root_work_dir / self._test_name / self._test_case_name

    def __str__(self):
        return '%s.%s' % (self._test_name, self._test_case_name)

    def get_arguments(self):
        log_level = TEST_LOG_LEVEL.get(self._test_name, DEFAULT_LOG_LEVEL)
        # developers asked for these flags to be used for unit tests
        return [
            '--gtest_break_on_failure',
            '--gtest_filter=%s' % self._test_case_name,
            '--log-level=%s' % log_level,
        ]

    @classmethod
    def is_test_suite(cls, executable_path, env):
        try:
            output = subprocess.check_output(
                [str(executable_path), '--help'],
                env=env,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
        except (subprocess.CalledProcessError, OSError):

            return False
        else:
            return '--gtest_list_tests' in output

    @classmethod
    def get_test_processes(cls, platform, env, work_dir, test_name, executable_path):
        output = subprocess.check_output([
            str(executable_path),
            '--gtest_list_tests',
            '--gtest_filter=-NxAssert*:-NxCritical*'],
            env=env,
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
                yield cls(
                    platform, env, work_dir, test_name,
                    test_case_name.replace('/', '_'), executable_path)
