import re
import argparse
from collections import deque
import abc
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)  # this logger is for parser debugging only


ERROR_LINE_COUNT_LIMIT = 1000  # errors can not be longer than this
MAX_ERROR_LINE_COUNT_SHOWN = 50  # do not show more than this lines
MAX_ERROR_LINE_LENGTH = 300  # strip at the middle of longer lines
SKIPPED_LINES_FORMAT = '[ skipped %d lines ]'


class Match(object):

    @classmethod
    def not_matched(cls, line):
        return cls(line=line, pattern=None)

    def __init__(self, pattern, line):
        self.pattern = pattern
        self._line = line

    @property
    def severity(self):
        if self.pattern:
            return self.pattern.severity
        else:
            return None

    @property
    def pattern_idx(self):
        if self.pattern:
            return self.pattern.idx
        else:
            return None

    def __repr__(self):
        return '<%s%s: %r>' % ('#%d/' % self.pattern_idx if self.pattern_idx else '', self.severity or 'none', self.line)

    def with_line(self, line):
        return Match(self.pattern, line)

    @property
    def line(self):
        max_len = MAX_ERROR_LINE_LENGTH
        if len(self._line) > max_len:
            return self._line[: max_len/2 ] + ' ... ' + self._line[ -max_len/2 :]
        else:
            return self._line


class MatchResult(object):

    # action values
    STORE = 'store'
    REJECT = 'reject'
    YIELD = 'yield'

    @classmethod
    def store(cls):
        return cls(cls.STORE)

    @classmethod
    def reject(cls):
        return cls(cls.REJECT)

    @classmethod
    def yield_(cls, pattern, line):
        return cls(cls.YIELD, Match(pattern, line))

    def __init__(self, action, match=None):
        self.action = action
        self.match = match  # Match, not None when action is YIELD

    def __repr__(self):
        if self.action == self.YIELD:
            return '<%s: %r>' % (self.action, self.match)
        else:
            return '<%s>' % self.action

    def with_lines(self, line_list):
        return [self.match.with_line(line) for line in line_list]

    @property
    def adjusted_match(self):
        return self.match.with_line(self._limit_line_length(self.match.line))


class Pattern(object):

    __metaclass__ = abc.ABCMeta

    def __init__(self, severity, pattern):
        self.severity = severity
        self.pattern = pattern
        self.idx = None

    def __repr__(self):
        return '<#%d>' % self.idx

    @abc.abstractmethod
    def match_line(self, line, line_idx=0):
        pass


class SingleLinePattern(Pattern):

    def __init__(self, severity, pattern):
        Pattern.__init__(self, severity, pattern)
        self.regexp = re.compile(pattern)

    def match_line(self, line, line_idx=0):
        if self.regexp.match(line):
            return MatchResult.yield_(self, line)
        else:
            return MatchResult.reject()


class MultiLinePattern(Pattern):

    def __init__(self, severity, first_line, last_line=None, second_line=None, other_lines=None):
        Pattern.__init__(
            self, severity,
            ' | '.join(filter(None, [first_line, second_line, other_lines, last_line])))
        self._first_line_re = re.compile(first_line)
        self._last_line_re = re.compile(last_line) if last_line else None
        self._second_line_re = re.compile(second_line) if second_line else None
        self._other_lines_re = re.compile(other_lines) if other_lines else None

    def match_line(self, line, line_idx=0):
        if line_idx == 0:
            return self._store_or_reject(self._first_line_re, line)
        if line_idx == 1 and self._second_line_re:
            return self._store_or_reject(self._second_line_re, line)
        if self._last_line_re.match(line):
            return MatchResult.yield_(self, line)
        if self._other_lines_re and not self._other_lines_re.match(line):
            return MatchResult.reject()
        return MatchResult.store()

    def _store_or_reject(self, re, line):
        if re.match(line):
            return MatchResult.store()
        else:
            return MatchResult.reject()


PATTERN_LIST = [
    # Linux
    SingleLinePattern('error', r'.+:\d+:\d+:\s+(\S+\s+)?error:'),
    #SingleLinePattern('error', r':\s+undefined reference to'),  # must be cought by multiline rule below
    SingleLinePattern('error', r'\s+Error\s+\d+'),
    SingleLinePattern('warning', r':\d+:\d+:\s+warning:'),
    SingleLinePattern('warning', r':\d+: Warning:'),  # [INFO] {standard input}:50870: Warning: end of file not at end of a line; newline inserted
    SingleLinePattern('error', r':\d+: Error:'),      # [INFO] {standard input}:51067: Error: unknown pseudo-op: `.lbe293'
    SingleLinePattern('error', r'internal compiler error:'),  # ..qmetatype.h:736:1: internal compiler error: Segmentation fault
    MultiLinePattern('error', r'FAILED:.+', last_line=r'collect2: error: .+'),
    # Windows
    MultiLinePattern('error', r'.+ALL_BUILD.vcxproj.+->$',
                         other_lines=r'.+-> ?$', last_line=r'.+:\s+(fatal\s)?error\s[A-Z]+\d+\s*:'),
    SingleLinePattern('error', r'.+:\s+(fatal\s)?error\s[A-Z]+\d+\s*:'),
    SingleLinePattern('warning', r'.+:\s+warning\s[A-Z]+\d+\s*:'),
    MultiLinePattern('error', r'ALL_BUILD\.vcxproj.+->', last_line=r'.*error.*:.+'),
    SingleLinePattern('error', r'\s*CUSTOMBUILD.*error.*:.+'),
    SingleLinePattern('error', r'\s+Error : .+'),
    # clang
    SingleLinePattern('error', r'ERROR:'),
    MultiLinePattern('error', r'In file included from .+:\d+',
                         other_lines=r'((In file included |\s+)from .+:\d+)|(\S+:)',
                         last_line=r'.+: error: .+'),
    SingleLinePattern('error', r'.+:\s+error:'),
    MultiLinePattern('error', r'FAILED:.+', last_line=r'clang: error: .+'),
    SingleLinePattern('error', r'make: \*\*\* \[.+\] Error .+'),  # ios
    # FAILED: : && /home/.../arm-linux-gnueabihf-g++ -fPIC -O3 ... \nld: symbol(s) not found for architecture 
    MultiLinePattern('error', r'FAILED:.+', other_lines=r'\s+.+', last_line=r'ld: .+$'),
    # Common
    SingleLinePattern('error', r'\[ERROR\]'),
    SingleLinePattern('warning', r'\[WARNING\]'),
    SingleLinePattern('warning', r'SKIPPED'),
    SingleLinePattern('success', r'SUCCESS'),
    MultiLinePattern('error', r'CMake Error: .+', other_lines=r'\s+.+', last_line=r'\w+.+'),
    MultiLinePattern('error', r'CMake Error at .+:', last_line=r'-- Configuring incomplete.+'),
    MultiLinePattern('error', r'\s*File ".+", line \d+', last_line=r'\s*SyntaxError: invalid syntax'),
    MultiLinePattern('error', r'rsync: .+', second_line=r'rsync error: .+', last_line=r'>> \[.+\]: FAILED'),
    MultiLinePattern('error', r'FAILED:.+', last_line=r'FAILURE \(status 1\); see the error message\(s\) above.'),  # ninja
    SingleLinePattern('error', r'FAILED:.+'),  # ninja
    ]


class Parser(object):

    def __init__(self):
        for idx, pattern in enumerate(PATTERN_LIST):
            pattern.idx = idx
            log.debug('pattern #%d: %s', idx, pattern.pattern)
        log.debug('-'*40)
        self._pending_lines = []
        self._parse_from_rule = 0
        self._current_pattern_lines = []
        self._current_pattern = None

    def parse_line_list(self, line_list):
        for new_line in line_list:
            log.debug('new line: %r', new_line)
            self._pending_lines = [new_line.rstrip('\r\n')]
            for match in self._parse_pending_lines():
                yield match
        while self._current_pattern_lines:
            log.debug('input is over, has %d pending pattern lines; reparsing...', len(self._current_pattern_lines))
            self._reject_pending_pattern()
            for match in self._parse_pending_lines():
                yield match
        log.debug('parsing is done.')

    def _parse_pending_lines(self):
        while self._pending_lines:
            line = self._pending_lines.pop(0)
            log.debug('  parsing line: %r', line)
            for match in self._parse_line(line):
                log.debug('    yielding %r', match)
                yield match
            if self._current_pattern:
                log.debug('    pending %r', self._current_pattern)

    def _parse_line(self, line):
        if self._current_pattern:
            return self._match_current_pattern(line)
        return self._match_first_line(line)

    def _match_first_line(self, line):
        parse_from_rule = self._parse_from_rule
        self._parse_from_rule = 0
        for pattern in PATTERN_LIST:
            if pattern.idx < parse_from_rule:
                continue
            result = pattern.match_line(line)
            if result.action == result.REJECT:
                continue
            log.debug('      first line: %r from %r for %r', result, pattern, line)
            if result.action == result.YIELD:
                return [result.match]
            if result.action == result.STORE:
                self._current_pattern_lines = [line]
                self._current_pattern = pattern
                return []
        log.debug('    first line: none matched')
        return [Match.not_matched(line)]

    def _match_current_pattern(self, line):
        if len(self._current_pattern_lines) >= ERROR_LINE_COUNT_LIMIT:
            self._current_pattern_lines.append(line)
            self._reject_pending_pattern()
            return []
        result = self._current_pattern.match_line(line, line_idx=len(self._current_pattern_lines))
        log.debug('      result from pending %r: %r', self._current_pattern, result)
        if result.action == result.STORE:
            self._current_pattern_lines.append(line)
            return []
        if result.action == result.YIELD:
            line_list = self._current_pattern_lines + [line]
            self._current_pattern_lines = []
            self._current_pattern = None
            return self._adjust_multi_line_result(result, line_list)
        if result.action == result.REJECT:
            self._current_pattern_lines.append(line)
            self._reject_pending_pattern()
            return []
        assert False, 'Unexpected action: %r' % result.action

    def _reject_pending_pattern(self):
        self._pending_lines = self._current_pattern_lines + self._pending_lines
        self._parse_from_rule = self._current_pattern.idx + 1
        self._current_pattern_lines = []
        self._current_pattern = None

    def _adjust_multi_line_result(self, result, line_list):
        line_list = list(filter(None, line_list))
        max_count = MAX_ERROR_LINE_COUNT_SHOWN
        if len(line_list) > max_count:
            line_list = (line_list[: max_count/2 ]
                             + [SKIPPED_LINES_FORMAT % (len(line_list) - max_count)]
                             + line_list[ -max_count/2 :])
        return result.with_lines(line_list)


def parse_output_lines(line_list):
    return Parser().parse_line_list(line_list)


def test_output():
    parser = argparse.ArgumentParser()
    parser.add_argument('severities', help='Which severities to reports, one chars for each: ewsn (n=none)')
    parser.add_argument('file', type=file, help='Build output to parse')
    args = parser.parse_args()
    for match in parse_output_lines(args.file):
        ch = match.severity[0] if match.severity else 'n'
        if ch in args.severities:
            print '%s\t%s\t%s' % (match.severity or 'none', match.pattern_idx if match.pattern_idx is not None else '-', match.line.rstrip())

if __name__ == '__main__':
    test_output()
