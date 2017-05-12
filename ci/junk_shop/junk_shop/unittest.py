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
from junk_shop.capture_repository import Parameters, DbCaptureRepository


ARTIFACT_LINE_COUNT_LIMIT = 10000
EXPECTED_CORE_PATTERN = '%e.core.%t.%p'
CORE_PATTERH_FILE = '/proc/sys/kernel/core_pattern'

GTEST_ARGUMENTS = [
    '--gtest_filter=-NxCritical.All3',
    '--gtest_shuffle',
    '--log-level=DEBUG2',
    ]

GDB_BACKTRACE_EXTRACT_COMMANDS = [
    r'set print static-members off',
    r'echo \n-- current thread backtrace --\n',
    r'bt',
    r'echo \n-- backtraces of all threads --\n',
    r'thread apply all backtrace',
    r'echo \n-- full backtraces of all threads --\n',
    r'thread apply all backtrace full',
    r'quit',
    ]


def extract_core_source_binary(core_path):
    # max ELF program sections processed, will get 'too many program headers' message overwise:
    phnum_arg = '-Pelf_phnum=10000'
    try:
        output = subprocess.check_output(['file', phnum_arg, core_path])
    except subprocess.CalledProcessError as x:
        print 'Error extracting core source binary from %s: %s' % (core_path, x)
        return None
    mo = re.match(r".*, from '(\S+).*'", output.rstrip())
    if mo:
        return mo.group(1)

def extract_core_backtrace(binary_path, gdb_path, core_path):
    print 'Extracting backtrace from %s, generated by %s' % (core_path, binary_path)
    args = [gdb_path, '--quiet', binary_path, core_path]
    for command in GDB_BACKTRACE_EXTRACT_COMMANDS:
        args += ['-ex', command]
    return subprocess.check_output(args)

def add_core_artifacts(repository, binary_path, gdb_path, run, artifact_path):
    fname = os.path.basename(artifact_path)
    with open(artifact_path, 'rb') as f:
        repository.add_artifact(run, fname, repository.artifact_type.core, f.read(), is_error=True)
    if not gdb_path or not binary_path: return
    backtrace = extract_core_backtrace(binary_path, gdb_path, artifact_path)
    if backtrace:
        repository.add_artifact(run, '%s-bt' % fname, repository.artifact_type.traceback, backtrace, is_error=True)


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

        def add_core_artifacts(self, binary_path, gdb_path, artifact_path):
            run = models.Run[self.run.id]
            add_core_artifacts(self._repository, binary_path, gdb_path, run, artifact_path)

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
                self._repository.add_artifact(run, name, type, data, is_error)

        def _produce_test_run(self, parent_run, root_name, suite, test):
            test_path = ['unit', root_name]
            is_test = False
            if suite:
                test_path.append(suite)
                if test:
                    test_path.append(test)
                    is_test = True
            return self._repository.produce_test_run(parent_run, test_path, is_test)


    def __init__(self, repository, config_vars, gdb_path, root_run, test_name, binary_path):
        if not os.path.exists(binary_path):
            raise RuntimeError('File %r does not exist' % binary_path)
        self._repository = repository
        self._config_vars = config_vars
        self._gdb_path = gdb_path
        self._root_run = root_run
        self._test_name = test_name  # aka executable file name
        self._binary_path = binary_path  # full path to test binary, *_ut
        self._pipe = None
        self._threads = []
        self._levels = [self.Level(self._repository, self._root_run, self._test_name)]  # Level list, [global, suite, test]
        self._current_suite = None
        self._current_test = None
        self._started_at = None
        self.my_core_files = set()

    def start(self):
        kind = os.path.basename(os.path.dirname(self._binary_path))
        env = dict(os.environ,
                   LD_LIBRARY_PATH=':'.join(
                       filter(None, [os.environ.get('LD_LIBRARY_PATH'),
                                     self._config_vars['LIB_PATH'],
                                     self._config_vars['QT_LIB']])))
        args = [self._binary_path] + GTEST_ARGUMENTS
        self._levels[0].add_stdout_line('[ command line: "%s" ]' % subprocess.list2cmdline(args))
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
        return self._pipe.poll() is not None

    def abort_on_timeout(self, run_duration):
        if not self.is_finished():
            print 'Aborting %s' % self._test_name
            if self._levels:
                self._levels[0].add_stdout_line(
                    '[ Aborted by timeout, still running after %s seconds ]' % run_duration.total_seconds())
            self._pipe.send_signal(signal.SIGABRT)
            self._pipe.wait()

    def wait(self):
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
            processor(line.rstrip('\n'))

    def _process_stdout_line(self, line):
        #if not self._current_test:
        #print '%s %s %s stdout: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._levels[0].add_full_stdout_line(line)
        log_pattern = '20\d\d-\d\d-\d\d .+'
        if self._current_test:
            mo = re.match(r'^\[\s+(OK|FAILED)\s+\] (%s)?%s\.%s(%s)?( \((\d+) ms\))?$'
                          % (log_pattern, self._current_suite, self._current_test, log_pattern), line)
            if mo:
                # handle log/output lines interleaved with gtest output:
                if mo.group(2):
                    self._levels[-1].add_stdout_line(mo.group(2))
                if mo.group(3):
                    self._levels[-1].add_stdout_line(mo.group(3))
                self._process_test_stop(line, mo.group(1), mo.group(5))
                return
        elif self._current_suite:
            mo = re.match(r'^\[\s+RUN\s+\] %s\.(\w+)$' % self._current_suite, line)
            if mo:
                self._process_test_start(line, mo.group(1))
                return
        if self._current_suite:
            mo = re.match(r'^\[----------\] \d+ tests? from %s \((\d+) ms total\)$' % self._current_suite, line)
            if mo:
                self._process_suite_stop(line, mo.group(1))
                return
        else:
            mo = re.match(r'^\[----------\] \d+ tests? from ([\w/]+)(, where .+)?(%s)?$' % log_pattern, line)
            if mo:
                if mo.group(2):  # handle log/output lines interleaved with gtest output
                    self._levels[-1].add_stdout_line(mo.group(3))
                self._process_suite_start(mo.group(1))
                return
        if line or self._current_suite:
            self._levels[-1].add_stdout_line(line)

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
        has_cores = False
        for path in glob.glob('*.core.*'):
            binary_path = extract_core_source_binary(path)
            if binary_path != self._binary_path:
                core_fname = path.split('.')[0]
                # core file name is truncated by linux to TASK_COMM_LEN - 1 (currently 16-1, will be 20-1)
                if not self._test_name.startswith(core_fname): continue  # not our core
            level.add_stdout_line('[ produced core file: %s ]' % path)
            level.add_core_artifacts(binary_path or self._binary_path, self._gdb_path, path)
            self.my_core_files.add(path)
            has_cores = True
        return has_cores


class TestRunner(object):

    @db_session
    def __init__(self, repository, timeout, bin_dir, binary_list):
        config_vars = self._read_current_config(bin_dir)
        self._repository = repository
        self._timeout = timeout  # timedelta
        self._started_at = None
        self._gdb_path = None
        self._core_files_belonging_to_tests = set()  # core files recognized by particular test
        self._errors = []
        self._root_run = repository.produce_test_run(root_run=None, test_path_list=['unit'])
        self._run_pre_checks(self._root_run)
        self._processes = [
            TestProcess(repository, config_vars, self._gdb_path, self._root_run, binary_name, os.path.join(bin_dir, binary_name))
            for binary_name in binary_list]

    def start(self):
        self._clean_core_files()
        self._started_at = datetime_utc_now()
        for process in self._processes:
            process.start()

    def wait(self):
        passed = True
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
                    passed = False
            time.sleep(1)
        with db_session:
            run = models.Run[self._root_run.id]
            has_cores = self._collect_core_files(run)
            run.outcome = status2outcome(passed and not has_cores)
            run.duration = datetime_utc_now() - self._started_at
            if self._errors:
                self._repository.add_artifact(
                    run, 'errors', self._repository.artifact_type.output, '\n'.join(self._errors), is_error=True)

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
        error_list = []
        try:
            self._gdb_path = subprocess.check_output(['which', 'gdb']).rstrip()
        except subprocess.CalledProcessError as x:
            error_list.append('gdb is missing: core files will not be parsed')
        core_pattern = subprocess.check_output(['cat', CORE_PATTERH_FILE]).rstrip()
        if core_pattern != EXPECTED_CORE_PATTERN:
            error_list.append('Core pattern is %r, but expected is %r; core files will not be collected. Set it in %s'
                              % (core_pattern, EXPECTED_CORE_PATTERN, CORE_PATTERH_FILE))
        core_ulimit = subprocess.check_output(['ulimit', '-c'], shell=True).rstrip()
        if core_ulimit != 'unlimited':
            error_list.append('ulimit for core files is %s, but expected is "unlimited"; core files may not be generated.'
                              ' Set it using command "ulimit -c unlimited"' % core_ulimit)
        if error_list:
            for error in error_list:
                print 'Environment configuration error:', error
            artifact_type = self._repository.artifact_type.output
            self._repository.add_artifact(root_run, 'warnings', artifact_type, '\n'.join(error_list), is_error=True)

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
            binary_path = extract_core_source_binary(path)
            add_core_artifacts(self._repository, binary_path, self._gdb_path, run, path)
            has_cores = True
        return has_cores


def check_is_dir(dir):
    if not os.path.isdir(dir):
        raise argparse.ArgumentTypeError('%s is not an existing directory' % dir)
    return os.path.abspath(dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parameters', type=Parameters.from_string, metavar=Parameters.example,
                        help='Run parameters')
    parser.add_argument('--timeout-sec', type=int, dest='timeout_sec', help='Run timeout, seconds')
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('bin_dir', type=check_is_dir, help='Directory to test binaries')
    parser.add_argument('test_binary', nargs='+', help='Executable for unit test, *_ut')
    args = parser.parse_args()
    timeout = timedelta(seconds=args.timeout_sec) if args.timeout_sec else None
    try:
        repository = DbCaptureRepository(args.db_config, args.parameters)
        runner = TestRunner(repository, timeout, args.bin_dir, args.test_binary)
        runner.start()
        runner.wait()
    except RuntimeError as x:
        print x
        sys.exit(1)


if __name__ == '__main__':
    main()
