#!/usr/bin/env python

# run unit tests, store results to database

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
from pony.orm import db_session
from junk_shop.utils import DbConfig, datetime_utc_now, status2outcome
from junk_shop import models
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository
from junk_shop.platform import create_platform


ARTIFACT_LINE_COUNT_LIMIT = 10000
CORE_FILE_SIZE_LIMIT = 100 * 1024*1024  # do not store core files larger than this

LOG_PATTERN = '20\d\d-\d\d-\d\d .+'

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
        print 'Core file %r is too large (%r); will not store' % (artifact_path, size)
    backtrace = platform.extract_core_backtrace(binary_path, artifact_path)
    if backtrace:
        repository.add_artifact(run, '%s-bt' % fname, '%s-bt' % fname, repository.artifact_type.traceback, backtrace, is_error=True)


class TestProcess(object):


    class Level(object):

        @db_session
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
            return
            if not self._stdout_lines and not self._stderr_lines: return
            print '----- %s -------------' % name
            for line in self._stdout_lines:
                print line
            if self._stderr_lines:
                print '----- stderr -----------'
            for line in self._stderr_lines:
                print line
            print '----------------------------'

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

        def _produce_test_run(self, parent_run, root_name, suite, test):
            test_path = ['unit', root_name]
            is_test = False
            if suite:
                test_path.append(suite)
                if test:
                    test_path.append(test)
                    is_test = True
            return self._repository.produce_test_run(parent_run, test_path, is_test)


    def __init__(self, repository, config_vars, platform, root_run, test_name, binary_path):
        self._repository = repository
        self._config_vars = config_vars
        self._platform = platform
        self._root_run = root_run
        self._test_name = test_name  # aka executable file name
        self._binary_path = binary_path  # full path to test binary, *_ut
        self._pipe = None
        self._threads = []
        self._levels = [self.Level(self._repository, self._root_run, self._test_name)]  # Level list, [global, suite, test]
        self._current_suite = None
        self._current_test = None
        self._last_stdout_line = None
        self._started_at = None
        self.my_core_files = set()

    def start(self):
        kind = os.path.basename(os.path.dirname(self._binary_path))
        env = self._platform.env_with_library_path(self._config_vars)
        args = [self._binary_path] + GTEST_ARGUMENTS
        self._levels[0].add_stdout_line('[ command line: "%s" ]' % subprocess.list2cmdline(args))
        if not os.path.exists(self._binary_path):
            print '%s: file %r is missing' % (self._test_name, self._binary_path)
            level = self._levels.pop()
            level.add_stderr_line('File %r does not exist' % self._binary_path)
            level.flush(passed=False)
            return
        self._pipe = subprocess.Popen(
            args,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        for f, processor in [(self._pipe.stdout, self._process_stdout_line),
                             (self._pipe.stderr, self._process_stderr_line)]:
            thread = threading.Thread(target=self._read_thread, args=(f, processor))
            thread.daemon = True
            thread.start()
            self._threads.append(thread)
        self._started_at = datetime_utc_now()
        print '%s is started' % self._test_name

    def is_finished(self):
        if not self._pipe: return True
        return self._pipe.poll() is not None

    def abort_on_timeout(self, run_duration):
        if not self.is_finished():
            print 'Aborting %s' % self._test_name
            if self._levels:
                self._levels[0].add_stdout_line(
                    '[ Aborted by timeout, still running after %s seconds ]' % run_duration.total_seconds())
            self._platform.abort_process(self._pipe)
            self._pipe.wait()

    def wait(self):
        if not self._pipe: return False
        return_code = self._pipe.wait()
        for thread in self._threads:
            thread.join()  # threads are still reading buffered output after process is already dead
        duration = datetime_utc_now() - self._started_at
        while len(self._levels) > 1:
            level = self._levels.pop()
            level.add_stdout_line('[ aborted ]')
            level.flush(passed=False)
        level = self._levels.pop()
        level.add_stdout_line('[ return code: %d ]' % return_code)
        has_cores = self._collect_core_files(level)
        passed = return_code == 0 and not has_cores
        level.flush(passed, duration)
        passed = level.passed and passed
        print '%s is %s' % (self._test_name, status2outcome(passed))
        return passed
        #print '%s return code: %d' % (self._test_name, return_code)
        
    def _read_thread(self, f, processor):
        for line in f:
            processor(line.rstrip('\r\n'))

    def _process_stdout_line(self, line):
        #if not self._current_test:
        #print '%s %s %s stdout: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._levels[0].add_full_stdout_line(line)
        if not self._match_gtest_message(line):
            if line or self._current_suite:
                self._levels[-1].add_stdout_line(line)
        self._last_stdout_line = line

    def _match_gtest_message(self, line):
        if self._match_gtest_message_to_line(line):
            return True
        if not self._last_stdout_line:
            return False
        return self._match_gtest_message_to_line(self._last_stdout_line + line)

    def _match_gtest_message_to_line(self, line):
        if self._current_test:
            mo = re.match(r'^(%s)?\[\s+(OK|FAILED)\s+\] (%s)?%s\.%s(%s)?( \((\d+) ms\))?$'
                          % (LOG_PATTERN, LOG_PATTERN, self._current_suite, self._current_test, LOG_PATTERN), line)
            if mo:
                # handle log/output lines interleaved with gtest output:
                if mo.group(3):
                    self._levels[-1].add_stdout_line(mo.group(3))
                if mo.group(4):
                    self._levels[-1].add_stdout_line(mo.group(4))
                self._process_test_stop(line, mo.group(2), mo.group(6))
                return True
        elif self._current_suite:
            mo = re.match(r'^\[\s+RUN\s+\] %s\.(\w+)$' % self._current_suite, line)
            if mo:
                self._process_test_start(line, mo.group(1))
                return True
        if self._current_suite:
            mo = re.match(r'^\[----------\] \d+ tests? from %s \((\d+) ms total\)$' % self._current_suite, line)
            if mo:
                self._process_suite_stop(line, mo.group(1))
                return True
        else:
            mo = re.match(r'^\[----------\] \d+ tests? from ([\w/]+)(, where .+)?(%s)?$' % LOG_PATTERN, line)
            if mo:
                if mo.group(2):  # handle log/output lines interleaved with gtest output
                    self._levels[-1].add_stdout_line(mo.group(3))
                self._process_suite_start(mo.group(1))
                return True
        return False

    def _parse_error(self, desc, line, suite, test=None):
        error = ('%s: binary: %s, current suite: %s, current test: %s, parsed suite: %s, parsed test: %s, line: %r'
                 % (desc, self._test_name, self._current_suite, self._current_test, suite, test, line))
        if self._levels:
            self._levels[0].add_parse_error(error)
        else:
            print 'parse error: %s' % error

    def _process_test_start(self, line, test):
        if self._current_test:
            self._parse_error('test closing is missing', line, suite, test)
        self._levels[-1].add_stdout_line(line)
        self._levels.append(self.Level(self._repository, self._levels[1].run, self._test_name, self._current_suite, test))
        self._current_test = test

    def _process_test_stop(self, line, status, duration_ms):
        assert len(self._levels) == 3, len(self._levels)
        passed = status == 'OK'
        level = self._levels.pop()
        level.report(self._current_suite + '.' + self._current_test)
        level.flush(passed, duration_ms=duration_ms)
        self._levels[-1].add_stdout_line(line)
        self._current_test = None
        if not passed:
            self._levels[-1].passed = False

    def _process_suite_start(self, suite):
        self._levels.append(self.Level(self._repository, self._levels[0].run, self._test_name, suite))
        self._current_suite = suite

    def _process_suite_stop(self, line, duration_ms):
        if self._current_test:
            self._parse_error('test %s closing tag is missing' % self._current_test, line, self._current_suite, self._current_test)
            assert len(self._levels) == 3, len(self._levels)
            level = self._levels.pop()
            level.flush(passed=False)
            self._current_test = None
            self._levels[-1].passed = False
        assert len(self._levels) == 2, len(self._levels)
        level = self._levels.pop()
        level.report(self._current_suite)
        level.flush(duration_ms=duration_ms)
        self._current_suite = None
        if not level.passed:
            self._levels[-1].passed = False
            
    def _process_stderr_line(self, line):
        #print '%s %s %s stderr: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._levels[-1].add_stderr_line(line)

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

    def __init__(self, repository, timeout, bin_dir, binary_list):
        self._repository = repository
        self._bin_dir = bin_dir
        self._binary_list = binary_list
        self._timeout = timeout  # timedelta
        self._started_at = None
        self._core_files_belonging_to_tests = set()  # core files recognized by particular test
        self._errors = []
        self._passed = True
        self._platform = create_platform()

    @db_session
    def start(self):
        config_vars = self._read_current_config(self._bin_dir)
        self._root_run = self._repository.produce_test_run(root_run=None, test_path_list=['unit'])
        self._run_pre_checks(self._root_run)
        self._processes = [
            TestProcess(self._repository, config_vars, self._platform, self._root_run,
                        self._binary_to_test_name(binary_name),
                        os.path.join(self._bin_dir, binary_name))
            for binary_name in self._binary_list]
        self._clean_core_files()
        self._started_at = datetime_utc_now()
        for process in self._processes:
            process.start()

    def wait(self):
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

    def finalize(self):
        with db_session:
            run = models.Run[self._root_run.id]
            has_cores = self._collect_core_files(run)
            run.outcome = status2outcome(self._passed and not has_cores)
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

    def _read_current_config(self, bin_dir):
        path = os.path.join(bin_dir, '../../../../build_variables/target/current_config.py')
        assert os.path.isfile(path), 'Current config file is required but is missing: %s' % path
        d = {}
        execfile(path, d)
        return d

    def _handle_timeout(self, run_duration):
        error = 'Timed out after %s seconds; aborted' % run_duration
        print error
        self._errors.append(error)
        for process in self._processes:
            process.abort_on_timeout(run_duration)

    def _run_pre_checks(self, root_run):
        error_list = self._platform.do_unittests_pre_checks()
        if not error_list: return
        for error in error_list:
            print 'Environment configuration error:', error
        artifact_type = self._repository.artifact_type.output
        self._repository.add_artifact(root_run, 'warnings', 'warnings', artifact_type, '\n'.join(error_list), is_error=True)

    def _clean_core_files(self):
        for path in glob.glob('*.core.*'):
            print 'Removing old core file %s' % path
            os.remove(path)

    def _collect_core_files(self, run):
        has_cores = False
        messages = []
        for path in glob.glob('*.core.*'):
            if path in self._core_files_belonging_to_tests: continue
            error = '[ produced core file: %s ]' % path
            print error
            self._errors.append(error)
            binary_path = self._platform.extract_core_source_binary(path)
            add_core_artifacts(self._platform, self._repository, binary_path, run, path)
            has_cores = True
        return has_cores


def check_is_dir(dir):
    if not os.path.isdir(dir):
        raise argparse.ArgumentTypeError('%s is not an existing directory' % dir)
    return os.path.abspath(dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--project', help='Junk-shop project name')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters')
    parser.add_argument('--timeout-sec', type=int, dest='timeout_sec', help='Run timeout, seconds')
    parser.add_argument('bin_dir', type=check_is_dir, help='Directory to test binaries')
    parser.add_argument('test_binary', nargs='+', help='Executable for unit test, *_ut')
    args = parser.parse_args()
    timeout = timedelta(seconds=args.timeout_sec) if args.timeout_sec else None
    repository = DbCaptureRepository(args.db_config, args.project, args.build_parameters)
    runner = TestRunner(repository, timeout, args.bin_dir, args.test_binary)
    try:
        runner.start()
        runner.wait()
    finally:
        runner.finalize()


if __name__ == '__main__':
    main()
