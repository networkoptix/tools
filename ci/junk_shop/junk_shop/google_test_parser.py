#!/bin/env python
# parse output of google tests
# TODO: parse errors

import abc
import re
import argparse
from collections import namedtuple


GTestPattern = namedtuple('GTestPattern', 'pattern extra_line_count')


LOG_PATTERN = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} +\w+ +[A-Z]+ .+'

GTEST_PATTERN_LIST = [
    GTestPattern(r'^.+:\d+: Failure$', 5),  # linux, mac
    GTestPattern(r'^unknown file: Failure$', 1),  # linux?, mac
    GTestPattern(r'^.+\(\d+\): error: .+$', 2),  # windows
    ]


class GoogleTestEventHandler(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def on_parse_error(self, error):
        pass

    @abc.abstractmethod
    def on_gtest_error(self, line):
        pass

    @abc.abstractmethod
    def on_output_line(self, line):
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
        self._last_output_line = None
        self._gtest_lines_left = None

    def process_line(self, line):
        line = line.rstrip('\r\n')
        if not self._match_line(line):
            if not self._last_output_line or not self._match_line(self._last_output_line + line):
                self._handle_output_line(line)
                self._last_output_line = line

    def finish(self, is_aborted=False):
        if self.current_test:
            if not is_aborted:
                self._parse_error('test closing tag is missing')
            self._handler.on_test_stop(None, None, is_aborted=True)
            self.current_test = None
        if self.current_suite:
            if not is_aborted:
                self._parse_error('suite closing tag is missing')
            self._handler.on_suite_stop(None)
            self.current_suite = None

    def _match_line(self, line):
        if self.current_test:
            if self._match_test_finish_signature(line):
                return True
        elif self.current_suite:
            if self._match_test_start_signature(line):
                return True
        if self.current_suite:
            if self._match_suite_finish_signature(line):
                return True
        else:
            if self._match_suite_start_signature(line):
                return True
        return False

    def _match_test_finish_signature(self, line):
        mo = re.match(r'^(.+)?\[\s+(OK|FAILED)\s+\] (.+)?%s\.%s(.*?)( \((\d+) ms\))?$'
                      % (self.current_suite, self.current_test), line)
        if not mo:
            return False
        # handle log/output lines interleaved with gtest output:
        if mo.group(1) or mo.group(3) or mo.group(4):
            self._handle_output_line((mo.group(1) or '') + (mo.group(3) or '') + (mo.group(4) or ''))
        self._handler.on_test_stop(mo.group(2), mo.group(6))
        self._handler.on_output_line(line)
        self.current_test = None
        return True

    def _match_test_start_signature(self, line):
        mo = re.match(r'^\[\s+RUN\s+\] %s\.(\w+)$' % self.current_suite, line)
        if not mo:
            return False
        if self.current_test:
            self._parse_error('test closing tag is missing', line, suite, test)
        test_name = mo.group(1)
        self._handler.on_output_line(line)
        self._handler.on_test_start(test_name)
        self.current_test = test_name
        return True

    def _match_suite_finish_signature(self, line):
        mo = re.match(r'^(.+)?\[----------\] (.+)?\d+ tests? from %s \((\d+) ms total\)$' % self.current_suite, line)
        if not mo:
            return False
        if mo.group(1) or mo.group(2):
            self._handle_output_line((mo.group(1) or '') + (mo.group(2) or ''))
        if self.current_test:
            self._parse_error('test closing tag is missing', line)
            self._handler.on_test_stop(None, None)
            self.current_test = None
        self._handler.on_suite_stop(mo.group(3))
        self._handler.on_output_line(line)
        self.current_suite = None
        return True

    def _match_suite_start_signature(self, line):
        mo = re.match(r'^(.+)?\[----------\] \d+ tests? from ([\w/]+)(, where .+)?(%s)?$' % LOG_PATTERN, line)
        if not mo:
            return False
        if mo.group(1) or mo.group(4):  # handle log/output lines interleaved with gtest output
            self._handle_output_line((mo.group(1) or '') + (mo.group(3) or ''))
        suite_name = mo.group(2)
        self._handler.on_output_line(line)
        self._handler.on_suite_start(suite_name)
        self.current_suite = suite_name
        return True

    def _handle_output_line(self, line):
        self._handler.on_output_line(line)
        if not self.current_test:
            return
        if self._gtest_lines_left:
            self._handler.on_gtest_error(line)
            self._gtest_lines_left -= 1
            return
        for pattern in GTEST_PATTERN_LIST:
            if re.match(pattern.pattern, line):
                self._handler.on_gtest_error(line)
                self._gtest_lines_left = pattern.extra_line_count
                break

    def _parse_error(self, desc, line=None, parsed_suite=None, parsed_test=None):
        error = ('%s: current suite: %s, current test: %s, parsed suite: %s, parsed test: %s, line: %r'
                 % (desc, self.current_suite, self.current_test, parsed_suite, parsed_test, line))
        self._handler.on_parse_error(error)


class TestEventHandler(GoogleTestEventHandler):

    def __init__(self, print_output, print_gtest_errors):
        self._print_output = print_output
        self._print_gtest_errors = print_gtest_errors

    def on_parse_error(self, error):
        print '*** Parse error: %s ***' % error

    def on_gtest_error(self, line):
        if self._print_gtest_errors:
            print '\tGTest: %s' % line.rstrip()

    def on_output_line(self, line):
        if self._print_output:
            print '\t%s' % line.rstrip()

    def on_suite_start(self, suite_name):
        print 'Suite: %s' % suite_name

    def on_suite_stop(self, duration_ms):
        print 'Suite finished: %s' % duration_ms
    
    def on_test_start(self, test_name):
        print 'Test: %s' % test_name

    def on_test_stop(self, status, duration_ms, is_aborted=False):
        print 'Test finished: %s %s, is_abourted=%r' % (status, duration_ms, is_aborted)


def test_output():
    parser = argparse.ArgumentParser()
    parser.add_argument('--print-output', '-s', action='store_true', help='Print output lines too')
    parser.add_argument('--print-gtest-errors', '-e', action='store_true', help='Print google test errors')
    parser.add_argument('file', help='Google test output to parse')
    args = parser.parse_args()
    handler = TestEventHandler(print_output=args.print_output, print_gtest_errors=args.print_gtest_errors)
    parser = GoogleTestParser(handler)
    for line in file(args.file):
        parser.process_line(line)
    parser.finish()

if __name__ == '__main__':
    test_output()
