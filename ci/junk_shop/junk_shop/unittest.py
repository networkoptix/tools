#!/usr/bin/env python

# run unit tests, store results to database

import logging
import os.path
import sys
import re
import glob
from collections import deque
from datetime import timedelta
import time
import argparse
import subprocess
import signal
import threading
from pony.orm import db_session, commit
from junk_shop.utils import DbConfig, datetime_utc_now, timedelta_to_str, status2outcome
from junk_shop import models
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
from junk_shop.platform import create_platform
from junk_shop.google_test_parser import GoogleTestEventHandler, GoogleTestParser

log = logging.getLogger(__name__)


ARTIFACT_LINE_COUNT_LIMIT = 100000
CORE_FILE_SIZE_LIMIT = 100 * 1024*1024  # do not store core files larger than this

GTEST_ARGUMENTS = [
    '--gtest_filter=-NxCritical.All3',
    '--gtest_shuffle',
    '--log-level=DEBUG2',
    ]

def add_core_artifacts(platform, repository, binary_path, run, artifact_path):
    fname = os.path.basename(artifact_path)
    size = os.stat(artifact_path).st_size
    if size <= CORE_FILE_SIZE_LIMIT:
        with open(artifact_path, 'rb') as f:
            repository.add_artifact(run, fname, fname, repository.artifact_type.core, f.read(), is_error=True)
    else:
        log.info('Core file %r is too large (%r); will not store', artifact_path, size)
    backtrace = platform.extract_core_backtrace(binary_path, artifact_path)
    if backtrace:
        repository.add_artifact(run, '%s-bt' % fname, '%s-bt' % fname, repository.artifact_type.traceback, backtrace, is_error=True)


class TestProcess(GoogleTestEventHandler):


    class Level(object):

        def __init__(self, repository, parent_run, root_name, suite=None, test=None):
            self._repository = repository
            self.run = self._produce_test_run(parent_run, root_name, suite, test)
            self._stdout_lines = deque(maxlen=ARTIFACT_LINE_COUNT_LIMIT)
            self._stderr_lines = deque(maxlen=ARTIFACT_LINE_COUNT_LIMIT)
            self._full_stdout_lines = deque(maxlen=ARTIFACT_LINE_COUNT_LIMIT)  # including descendant stdout
            self._parse_errors = deque(maxlen=ARTIFACT_LINE_COUNT_LIMIT)
            self.passed = True

        def add_stdout_line(self, line):
            self._stdout_lines.append(line)

        def add_stderr_line(self, line):
            self._stderr_lines.append(line)

        def add_full_stdout_line(self, line):
            self._full_stdout_lines.append(line)

        def add_parse_error(self, line):
            self._parse_errors.append(line)

        def add_core_artifacts(self, platform, binary_path, artifact_path):
            run = models.Run[self.run.id]
            add_core_artifacts(platform, self._repository, binary_path, run, artifact_path)

        def report(self, name):
            if not self._stdout_lines and not self._stderr_lines: return
            log.debug('----- %s -------------', name)
            for line in self._stdout_lines:
                log.debug(line)
            if self._stderr_lines:
                log.debug('----- stderr -----------')
            for line in self._stderr_lines:
                log.debug(line)
            log.debug('----------------------------')

        @db_session
        def flush(self, passed=True, duration=None, duration_ms=None):
            run = models.Run[self.run.id]
            run.outcome = status2outcome(self.passed and passed)
            if duration_ms is not None:
                duration = timedelta(milliseconds=int(duration_ms))
            if duration is not None:
                run.duration = duration
            self._add_artifact(run, 'stdout', self._repository.artifact_type.output, self._stdout_lines)
            self._add_artifact(run, 'stderr', self._repository.artifact_type.output, self._stderr_lines, is_error=True)
            self._add_artifact(run, 'full stdout', self._repository.artifact_type.output, self._full_stdout_lines)
            self._add_artifact(run, 'parse errors', self._repository.artifact_type.output, self._parse_errors, is_error=True)

        def _add_artifact(self, run, name, type, lines, is_error=False):
            if lines:
                data = '\n'.join(line for line in lines if line is not None)
                if len(lines) == lines.maxlen:
                    data = '[ truncated to %d lines ]\n' % lines.maxlen + data
                self._repository.add_artifact(run, name, '%s-%s' % (self.run.name, name.replace(' ', '-')), type, data, is_error)

        @db_session
        def _produce_test_run(self, parent_run, root_name, suite, test):
            test_path = ['unit', root_name]
            is_test = False
            if suite:
                test_path.append(suite)
                if test:
                    test_path.append(test)
                    is_test = True
            return self._repository.produce_test_run(parent_run, test_path, is_test)


    def __init__(self, repository, config_vars, work_dir, platform, root_run, test_name, binary_path):
        self._repository = repository
        self._config_vars = config_vars
        self._work_dir = work_dir
        self._platform = platform
        self._root_run = root_run
        self._test_name = test_name  # aka executable file name
        self._binary_path = binary_path  # full path to test binary, *_ut
        self._pipe = None
        self._threads = []
        self._levels = [self.Level(self._repository, self._root_run, self._test_name)]  # Level list, [global, suite, test]
        self._parser = GoogleTestParser(self)
        self._started_at = None
        self._aborted = False
        self.my_core_files = set()

    def start(self):
        kind = os.path.basename(os.path.dirname(self._binary_path))
        env = self._platform.env_with_library_path(self._config_vars)
        args = [
            self._binary_path,
            '--tmp=%s' % self._work_dir,
            ] + GTEST_ARGUMENTS
        self._levels[0].add_stdout_line('[ command line: "%s" ]' % subprocess.list2cmdline(args))
        if not os.path.exists(self._binary_path):
            self._save_start_error('File %r is missing' % self._binary_path)
            return
        try:
            self._pipe = subprocess.Popen(
                args,
                cwd=self._work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                )
        except OSError as x:
            self._save_start_error('Error starting %r: %s' % (self._binary_path, x))
            return
        for f, processor in [(self._pipe.stdout, self._process_stdout_line),
                             (self._pipe.stderr, self._process_stderr_line)]:
            thread = threading.Thread(target=self._read_thread, args=(f, processor))
            thread.daemon = True
            thread.start()
            self._threads.append(thread)
        self._started_at = datetime_utc_now()
        log.info('%s is started', self._test_name)

    def _save_start_error(self, message):
        log.warning('%s: %s', self._test_name, message)
        level = self._levels.pop()
        level.add_stderr_line(message)
        level.flush(passed=False)

    def is_finished(self):
        if not self._pipe: return True
        return self._pipe.poll() is not None

    def abort_on_timeout(self, run_duration):
        if not self.is_finished():
            log.warning('Aborting %s', self._test_name)
            if self._levels:
                self._levels[0].add_stdout_line(
                    '[ Aborted by timeout, still running after %s seconds ]' % run_duration.total_seconds())
            self._aborted = True
            self._platform.abort_process(self._pipe)
            self._pipe.wait()

    def wait(self):
        if not self._pipe: return False
        return_code = self._pipe.wait()
        for thread in self._threads:
            thread.join()  # threads are still reading buffered output after process is already dead
        if self._aborted:
            for level in self._levels:
                level.add_stdout_line('[ aborted ]')
        self._parser.finish(self._aborted)
        duration = datetime_utc_now() - self._started_at
        level = self._levels.pop()
        level.add_stdout_line('[ return code: %d ]' % return_code)
        has_cores = self._collect_core_files(level)
        passed = return_code == 0 and not has_cores
        level.flush(passed, duration)
        passed = level.passed and passed
        log.info('%s is %s', self._test_name, status2outcome(passed))
        return passed
        #print '%s return code: %d' % (self._test_name, return_code)
        
    def _read_thread(self, f, processor):
        for line in f:
            processor(line.rstrip('\r\n'))

    def _process_stderr_line(self, line):
        #print '%s %s %s stderr: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._levels[-1].add_stderr_line(line)

    def _process_stdout_line(self, line):
        #if not self._current_test:
        #print '%s %s %s stdout: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._levels[0].add_full_stdout_line(line)
        self._parser.process_line(line)

    def on_parse_error(self, error):
        message = '%s: %s' % (self._test_name, error)
        if self._levels:
            self._levels[0].add_parse_error(message)
        else:
            log.warning('parse error: %s', message)

    def on_stdout_line(self, line):
        self._levels[-1].add_stdout_line(line)

    def on_suite_start(self, suite_name):
        self._levels.append(self.Level(self._repository, self._levels[0].run, self._test_name, suite_name))

    def on_suite_stop(self, duration_ms):
        assert len(self._levels) == 2, len(self._levels)
        level = self._levels.pop()
        level.report(self._parser.current_suite)
        level.flush(duration_ms=duration_ms)
        if not level.passed:
            self._levels[-1].passed = False

    def on_test_start(self, test_name):
        self._levels.append(self.Level(
            self._repository, self._levels[1].run, self._test_name, self._parser.current_suite, test_name))

    def on_test_stop(self, status, duration_ms):
        assert len(self._levels) == 3, len(self._levels)
        passed = status == 'OK'
        level = self._levels.pop()
        level.report(self._parser.current_suite + '.' + self._parser.current_test)
        level.flush(passed, duration_ms=duration_ms)
        if not passed:
            self._levels[-1].passed = False

    @db_session
    def _collect_core_files(self, level):
        if sys.platform == 'win32':
            return False
        has_cores = False
        for path in glob.glob('*.core.*'):
            binary_path = self._platform.extract_core_source_binary(path)
            if binary_path != self._binary_path:
                core_fname = path.split('.')[0]
                # core file name is truncated by linux to TASK_COMM_LEN - 1 (currently 16-1, will be 20-1)
                if not self._test_name.startswith(core_fname): continue  # not our core
            level.add_stdout_line('[ produced core file: %s ]' % path)
            level.add_core_artifacts(self._platform, binary_path or self._binary_path, path)
            self.my_core_files.add(path)
            has_cores = True
        return has_cores


class TestRunner(object):

    def __init__(self, repository, config_path, work_dir, bin_dir, binary_list, timeout):
        self._repository = repository
        self._config_path = config_path
        self._work_dir = work_dir
        self._bin_dir = bin_dir
        self._binary_list = binary_list
        self._timeout = timeout  # timedelta
        self._started_at = None
        self._core_files_belonging_to_tests = set()  # core files recognized by particular test
        self._errors = []
        self._passed = False
        self._platform = create_platform()
        self._root_run = None

    @db_session
    def init(self):
        self._started_at = datetime_utc_now()
        self._root_run = self._repository.produce_test_run(root_run=None, test_path_list=['unit'])
        commit()
        self._run_pre_checks(self._root_run)

    def start(self):
        config_vars = self._read_current_config()
        self._processes = [
            TestProcess(self._repository, config_vars, self._work_dir, self._platform, self._root_run,
                        self._binary_to_test_name(binary_name),
                        os.path.join(self._bin_dir, binary_name))
            for binary_name in self._binary_list]
        self._clean_core_files()
        for process in self._processes:
            process.start()

    def wait(self):
        self._passed = True
        while self._processes:
            run_duration = datetime_utc_now() - self._started_at
            if self._timeout and run_duration > self._timeout:
                self._handle_timeout(run_duration)
            for process in self._processes[:]:
                if not process.is_finished(): continue
                test_passed = process.wait()
                self._core_files_belonging_to_tests |= process.my_core_files
                self._processes.remove(process)
                if not test_passed:
                    self._passed = False
            time.sleep(1)

    def add_error(self, message):
        self._errors.append(message)

    @property
    def is_passed(self):
        return self._passed

    @db_session
    def finalize(self):
        if not self._root_run:
            return
        run = models.Run[self._root_run.id]
        has_cores = self._collect_core_files(run)
        if has_cores:
            self._passed = False
        run.outcome = status2outcome(self._passed)
        run.duration = datetime_utc_now() - self._started_at
        if self._errors:
            self._repository.add_artifact(
                run, 'errors', 'errors', self._repository.artifact_type.output, '\n'.join(self._errors), is_error=True)

    @staticmethod
    def _binary_to_test_name(binary_name):
        if sys.platform == 'win32' and binary_name.endswith('.exe'):
            return binary_name[:-len('.exe')]
        else:
            return binary_name

    def _read_current_config(self):
        assert os.path.isfile(self._config_path), 'Current config file is required but is missing: %s' % self._config_path
        d = {}
        execfile(self._config_path, d)
        return d

    def _handle_timeout(self, run_duration):
        error = 'Timed out after %s seconds; aborted' % timedelta_to_str(run_duration)
        log.warning(error)
        self._errors.append(error)
        for process in self._processes:
            process.abort_on_timeout(run_duration)

    def _run_pre_checks(self, root_run):
        error_list = self._platform.do_unittests_pre_checks()
        if not error_list: return
        for error in error_list:
            log.warning('Environment configuration error: %s', error)
        artifact_type = self._repository.artifact_type.output
        self._repository.add_artifact(root_run, 'warnings', 'warnings', artifact_type, '\n'.join(error_list), is_error=True)

    def _clean_core_files(self):
        for path in glob.glob('*.core.*'):
            log.info('Removing old core file %s', path)
            os.remove(path)

    def _collect_core_files(self, run):
        has_cores = False
        messages = []
        for path in glob.glob('*.core.*'):
            if path in self._core_files_belonging_to_tests: continue
            error = '[ produced core file: %s ]' % path
            log.info(error)
            self._errors.append(error)
            binary_path = self._platform.extract_core_source_binary(path)
            add_core_artifacts(self._platform, self._repository, binary_path, run, path)
            has_cores = True
        return has_cores


def check_is_dir(dir):
    if not os.path.isdir(dir):
        raise argparse.ArgumentTypeError('%s is not an existing directory' % dir)
    return os.path.abspath(dir)

def check_is_file(path):
    if not os.path.isfile(path):
        raise argparse.ArgumentTypeError('%s is not an existing file' % path)
    return os.path.abspath(path)

def run_unit_tests(repository, config_path, work_dir, bin_dir, test_binary_list, timeout):
    assert timeout is None or isinstance(timeout, timedelta), repr(timeout)
    runner = TestRunner(repository, config_path, work_dir, bin_dir, test_binary_list, timeout)
    try:
        runner.init()
        runner.start()
        runner.wait()
        return runner.is_passed
    except Exception as x:
        runner.add_error('Internal unittest.py error: %r' % x)
        raise
    finally:
        runner.finalize()



def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters')
    parser.add_argument('--timeout-sec', type=int, dest='timeout_sec', help='Run timeout, seconds')
    parser.add_argument('config_path', type=check_is_file, help='Path to current_config.py')
    parser.add_argument('bin_dir', type=check_is_dir, help='Directory to test binaries')
    parser.add_argument('test_binary', nargs='+', help='Executable for unit test, *_ut')
    args = parser.parse_args()
    work_dir = os.getcwd()
    timeout = timedelta(seconds=args.timeout_sec) if args.timeout_sec else None
    setup_logging()
    repository = DbCaptureRepository(args.db_config, args.build_parameters)
    is_passed = run_unit_tests(repository, args.config_path, work_dir, args.bin_dir, args.test_binary, timeout)
    if not is_passed:
        sys.exit(1)


if __name__ == '__main__':
    main()
