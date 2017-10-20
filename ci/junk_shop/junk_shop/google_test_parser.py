#!/bin/env python
# parse output of google tests

import abc
import re
import argparse


class GoogleTestEventHandler(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def on_parse_error(self, error):
        pass

    @abc.abstractmethod
    def on_stdout_line(self, line):
        pass

    @abc.abstractmethod
    def on_suite_start(self, suite_name):
        pass

    @abc.abstractmethod
    def on_suite_stop(self, duration_ms):
        pass
    
    @abc.abstractmethod
    def on_test_start(self, test_name):
        pass

    @abc.abstractmethod
    def on_test_stop(self, status, duration_ms):
        pass


class GoogleTestParser(object):

    def __init__(self, handler):
        self._handler = handler
        self.current_suite = None
        self.current_test = None
        self._last_stdout_line = None

    def process_line(self, line):
        if not self._match_line(line):
            if not self._last_stdout_line or not self._match_line(self._last_stdout_line + line):
                self._handler.on_stdout_line(line)
        self._last_stdout_line = line

    def finish(self):
        if self.current_test:
            self._parse_error('test closing tag is missing')
            self._handler.on_test_stop(None, None)
            self.current_test = None
        if self.current_suite:
            self._parse_error('suite closing tag is missing')
            self._handler.on_suite_stop(None)
            self.current_suite = None

    def _match_line(self, line):
        if self.current_test:
            mo = re.match(r'^(.+)?\[\s+(OK|FAILED)\s+\] (.+)?%s\.%s(.*?)( \((\d+) ms\))?$'
                          % (self.current_suite, self.current_test), line)
            if mo:
                # handle log/output lines interleaved with gtest output:
                if mo.group(1) or mo.group(3) or mo.group(4):
                    self._handler.on_stdout_line((mo.group(1) or '') + (mo.group(3) or '') + (mo.group(4) or ''))
                self._handler.on_test_stop(mo.group(2), mo.group(6))
                self._handler.on_stdout_line(line)
                self.current_test = None
                return True
        elif self.current_suite:
            mo = re.match(r'^\[\s+RUN\s+\] %s\.(\w+)$' % self.current_suite, line)
            if mo:
                if self.current_test:
                    self._parse_error('test closing tag is missing', line, suite, test)
                test_name = mo.group(1)
                self._handler.on_stdout_line(line)
                self._handler.on_test_start(test_name)
                self.current_test = test_name
                return True
        if self.current_suite:
            mo = re.match(r'^\[----------\] \d+ tests? from %s \((\d+) ms total\)$' % self.current_suite, line)
            if mo:
                if self.current_test:
                    self._parse_error('test closing tag is missing', line)
                    self._handler.on_test_stop(None, None)
                    self.current_test = None
                self._handler.on_suite_stop(mo.group(1))
                self._handler.on_stdout_line(line)
                self.current_suite = None
                return True
        else:
            mo = re.match(r'^(.+)?\[----------\] \d+ tests? from ([\w/]+)(, where .+)?(.+)?$', line)
            if mo:
                if mo.group(1) or mo.group(3):  # handle log/output lines interleaved with gtest output
                    self._handler.on_stdout_line((mo.group(1) or '') + (mo.group(3) or ''))
                suite_name = mo.group(2)
                self._handler.on_stdout_line(line)
                self._handler.on_suite_start(suite_name)
                self.current_suite = suite_name
                return True
        return False

    def _parse_error(self, desc, line=None, parsed_suite=None, parsed_test=None):
        error = ('%s: current suite: %s, current test: %s, parsed suite: %s, parsed test: %s, line: %r'
                 % (desc, self.current_suite, self.current_test, parsed_suite, parsed_test, line))
        self._handler.on_parse_error(error)


class TestEventHandler(GoogleTestEventHandler):

    def __init__(self, print_lines):
        self._print_lines = print_lines

    def on_parse_error(self, error):
        print '*** Parse error: %s ***' % error

    def on_stdout_line(self, line):
        if self._print_lines:
            print '\t%s' % line.rstrip()

    def on_suite_start(self, suite_name):
        print 'Suite: %s' % suite_name

    def on_suite_stop(self, duration_ms):
        print 'Suite finished: %s' % duration_ms
    
    def on_test_start(self, test_name):
        print 'Test: %s' % test_name

    def on_test_stop(self, status, duration_ms):
        print 'Test finished: %s %s' % (status, duration_ms)


def test_output():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true', help='Output stdout lines too')
    parser.add_argument('file', help='Google test output to parse')
    args = parser.parse_args()
    handler = TestEventHandler(print_lines=args.verbose)
    parser = GoogleTestParser(handler)
    for line in file(args.file):
        parser.process_line(line)
    parser.finish()

if __name__ == '__main__':
    test_output()
