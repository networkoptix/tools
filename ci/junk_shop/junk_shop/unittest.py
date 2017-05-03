#!/usr/bin/env python

# run unit tests, store results to database

import os.path
import sys
import re
from datetime import timedelta
import argparse
import subprocess
import threading
from pony.orm import db_session
from junk_shop.utils import DbConfig, datetime_utc_now
from junk_shop import models
from junk_shop.capture_repository import Parameters, DbCaptureRepository


def status2outcome(passed):
    if passed:
        return 'passed'
    else:
        return 'failed'


class TestProcess(object):

    class Output(object):

        @db_session
        def __init__(self, repository, parent_run, root_name, suite=None, test=None):
            self.repository = repository
            self.run = self._produce_test_run(parent_run, root_name, suite, test)
            self.stdout_lines = []
            self.stderr_lines = []
            self.passed = True

        def report(self, name):
            return
            if not self.stdout_lines and not self.stderr_lines: return
            print '----- %s -------------' % name
            for line in self.stdout_lines:
                print line
            if self.stderr_lines:
                print '----- stderr -----------'
            for line in self.stderr_lines:
                print line
            print '----------------------------'

        @db_session
        def flush(self, passed=True, duration=None, duration_ms=None):
            run = models.Run[self.run.id]
            run.outcome = status2outcome(passed)
            if duration_ms is not None:
                duration = timedelta(milliseconds=int(duration_ms))
            if duration is not None:
                run.duration = duration
            if self.stdout_lines:
                self.repository.add_artifact(
                    run, 'stdout', self.repository.artifact_type.output, '\n'.join(self.stdout_lines))
            if self.stderr_lines:
                self.repository.add_artifact(
                    run, 'stderr', self.repository.artifact_type.output, '\n'.join(self.stderr_lines))

        def _produce_test_run(self, parent_run, root_name, suite, test):
            test_path = ['unit', root_name]
            is_test = False
            if suite:
                test_path.append(suite)
                if test:
                    test_path.append(test)
                    is_test = True
            return self.repository.produce_test_run(parent_run, test_path, is_test)

    def __init__(self, repository, config_vars, root_run, test_name, binary_path):
        if not os.path.exists(binary_path):
            raise RuntimeError('File %r does not exist' % binary_path)
        self._repository = repository
        self._config_vars = config_vars
        self._root_run = root_run
        self._test_name = test_name
        self._binary_path = binary_path
        self._pipe = None
        self._threads = []
        self._output = [self.Output(self._repository, self._root_run, self._test_name)]  # Output list, [global, suite, test]
        self._current_suite = None
        self._current_test = None
        self._started_at = None

    def start(self):
        kind = os.path.basename(os.path.dirname(self._binary_path))
        env = dict(os.environ,
                   LD_LIBRARY_PATH=':'.join(
                       filter(None, [os.environ.get('LD_LIBRARY_PATH'),
                                     self._config_vars['LIB_PATH'],
                                     self._config_vars['QT_LIB']])))
        args = [self._binary_path,
                '--gtest_filter=-NxCritical.All3',
                '--gtest_shuffle',
                '--tmp=',
                '--log-file=/',
                '--log-size=20M',
                '--log-level=DEBUG2',
                ]
        self._output[0].stdout_lines.append('[ command line: "%s" ]' % subprocess.list2cmdline(args))
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

    def stop(self):
        if self._pipe.poll() is None:
            self._pipe.kill()
        self.wait()

    def wait(self):
        return_code = self._pipe.wait()
        for thread in self._threads:
            thread.join()  # threads are still reading buffered output after process is already dead
        passed = return_code == 0
        duration = datetime_utc_now() - self._started_at
        output = self._output.pop()
        output.stdout_lines.append('[ return code: %d ]' % return_code)
        output.report('global')
        output.flush(passed, duration)
        passed = output.passed and passed
        print '%s is %s' % (self._test_name, status2outcome(passed))
        return passed
        #print '%s return code: %d' % (self._test_name, return_code)
        
    def _read_thread(self, f, processor):
        for line in f:
            processor(line.rstrip('\n'))

    def _process_stdout_line(self, line):
        #if not self._current_test:
        #print '%s %s %s stdout: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        mo = re.match(r'^\[\s+(RUN|OK|FAILED)\s+\] (\w+)\.(\w+)( \((\d+) ms\))?', line)
        if mo:
            self._process_test_start_stop(line, mo.group(1), mo.group(2), mo.group(3), mo.group(5))
            return
        mo = re.match(r'^\[----------\] \d+ tests? from (\w+)( \((\d+) ms total\))?$', line)
        if mo:
            self._process_suite_start_stop(line, mo.group(1), mo.group(3))
            return
        if line or self._current_suite:
            self._output[-1].stdout_lines.append(line)

    def _process_test_start_stop(self, line, status, suite, test, duration_ms):
        assert suite == self._current_suite
        if status == 'RUN':
            assert not self._current_test
            self._output[-1].stdout_lines.append(line)
            self._output.append(self.Output(self._repository, self._output[1].run, self._test_name, self._current_suite, test))
            self._current_test = test
        else:
            assert test == self._current_test
            passed = status == 'OK'
            output = self._output.pop()
            output.report(self._current_suite + '.' + self._current_test)
            output.flush(passed, duration_ms=duration_ms)
            self._output[-1].stdout_lines.append(line)
            self._current_test = None
            if not passed:
                self.output[-1].passed = False

    def _process_suite_start_stop(self, line, suite, duration_ms):
        if duration_ms is not None:
            assert suite == self._current_suite
            output = self._output.pop()
            output.report(self._current_suite)
            output.flush(duration_ms=duration_ms)
            self._current_suite = None
            if not output.passed:
                self.output[-1].passed = False
        else:
            assert not self._current_suite
            self._output.append(self.Output(self._repository, self._output[0].run, self._test_name, suite))
            self._current_suite = suite
            
    def _process_stderr_line(self, line):
        #print '%s %s %s stderr: %r' % (self._test_name, self._current_suite or '-', self._current_test or '-', line)
        self._output[-1].stderr_lines.append(line)


class TestRunner(object):

    @db_session
    def __init__(self, repository, bin_dir, binary_list):
        config_vars = self._read_current_config(bin_dir)
        self._started_at = None
        self._root_run = repository.produce_test_run(root_run=None, test_path_list=['unit'])
        self._processes = [
            TestProcess(repository, config_vars, self._root_run, binary_name, os.path.join(bin_dir, binary_name))
            for binary_name in binary_list]

    def start(self):
        self._started_at = datetime_utc_now()
        for process in self._processes:
            process.start()

    def wait(self):
        passed = True
        for process in self._processes:
            test_passed = process.wait()
            if not test_passed:
                passed = False
        with db_session:
            run = models.Run[self._root_run.id]
            run.outcome = status2outcome(passed)
            run.duration = datetime_utc_now() - self._started_at

    def _read_current_config(self, bin_dir):
        path = os.path.join(bin_dir, '../../../../build_variables/target/current_config.py')
        assert os.path.isfile(path), 'Current config file is required but is missing: %s' % path
        d = {}
        execfile(path, d)
        return d


def check_is_dir(dir):
    if not os.path.isdir(dir):
        raise argparse.ArgumentTypeError('%s is not an existing directory' % dir)
    return os.path.abspath(dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parameters', type=Parameters.from_string, metavar=Parameters.example,
                        help='Run parameters')
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('bin_dir', type=check_is_dir, help='Directory to test binaries')
    parser.add_argument('test_binary', nargs='+', help='Executable for unit test, *_ut')
    args = parser.parse_args()
    try:
        repository = DbCaptureRepository(args.db_config, args.parameters)
        runner = TestRunner(repository, args.bin_dir, args.test_binary)
        runner.start()
        runner.wait()
    except RuntimeError as x:
        print x
        sys.exit(1)


if __name__ == '__main__':
    main()
