import re
import argparse


CONTEXT_SIZE = 100  # attempt to parse no more than this lines count at once


class Pattern(object):

    def __init__(self, severity):
        self.severity = severity

    def match_line(self, line):
        return None

    def match_context(self, line_list):
        return None


class SingleLinePattern(Pattern):

    def __init__(self, severity, pattern):
        Pattern.__init__(self, severity)
        self.regexp = re.compile(pattern)

    def match_line(self, line):
        if self.regexp.search(line):
            return self.severity


class MultiLinePattern(Pattern):

    def __init__(self, severity, pattern):
        Pattern.__init__(self, severity)
        self.regexp = re.compile(pattern, re.MULTILINE)

    def match_context(self, line_list):
        mo = self.regexp.search('\n'.join(line_list))
        if not mo:
            return None
        matched_line_count = len(mo.group(0).splitlines())
        return (matched_line_count, self.severity)


PATTERN_LIST = [
    # Linux
    SingleLinePattern('error', r':\d+:\d+:\s+(\S+\s+)?error:'),
    SingleLinePattern('error', r':\s+error:'),
    #SingleLinePattern('error', r':\s+undefined reference to'),  # must be cought by multiline rule below
    SingleLinePattern('error', r'\s+Error\s+\d+'),
    SingleLinePattern('warning', r':\d+:\d+:\s+warning:'),
    SingleLinePattern('warning', r':\d+: Warning:'),  # [INFO] {standard input}:50870: Warning: end of file not at end of a line; newline inserted
    SingleLinePattern('error', r':\d+: Error:'),      # [INFO] {standard input}:51067: Error: unknown pseudo-op: `.lbe293'
    SingleLinePattern('error', r'internal compiler error:'),  # ..qmetatype.h:736:1: internal compiler error: Segmentation fault
    MultiLinePattern('error', r'^FAILED:.+(\n.+)+\ncollect2: error: .+'),
    MultiLinePattern('error', r'^FAILED:.+(\n.+)+\nninja: build stopped: subcommand failed.'),
    # Windows
    SingleLinePattern('error', r':\s+(fatal\s)?error\s[A-Z]+\d+\s*:'),
    SingleLinePattern('warning', r':\s+warning\s[A-Z]+\d+\s*:'),
    # Mac
    SingleLinePattern('error', r'ERROR:'),
    # FAILED: : && /home/.../arm-linux-gnueabihf-g++ -fPIC -O3 ... \nld: symbol(s) not found for architecture 
    MultiLinePattern('error', r'^FAILED:.+\n:.+\nUndefined symbols.+\n(\s+.+\n)+ld: .+$'),
    # Common
    SingleLinePattern('error', r'\[ERROR\]'),
    SingleLinePattern('error', r'FAILURE'),
    SingleLinePattern('warning', r'\[WARNING\]'),
    SingleLinePattern('warning', r'SKIPPED'),
    SingleLinePattern('success', r'SUCCESS'),
    MultiLinePattern('error', r'^CMake Error: .+\n(\s+.+\n)+\w+.+'),
    MultiLinePattern('error', r'^CMake Error at .+:\n(.*\n)+-- Configuring incomplete.+'),
    MultiLinePattern('error', r'^\s*File ".+", line \d+\n(.*\n)+\s*SyntaxError: invalid syntax'),
    MultiLinePattern('error', r'^(rsync: .+\n)+rsync error: .+\n(.+\n)*>> \[.+\]: FAILED'),
    ]


def match_line(line):
    for rule_idx, pattern in enumerate(PATTERN_LIST):
        severity = pattern.match_line(line)
        if severity:
            return (rule_idx, severity)
    return (None, None)

def match_context(line_list):
    for rule_idx, pattern in enumerate(PATTERN_LIST):
        matched_line_count_and_severity = pattern.match_context(line_list)
        if matched_line_count_and_severity:
            return (rule_idx,) + matched_line_count_and_severity
    return (None, None, None)

def parse_output_lines(line_list):
    context = []
    for line in line_list:
        line = line.rstrip('\r\n')
        context = (context + [line])[-CONTEXT_SIZE:]  # drop oldest lines out of context
        rule_idx, matched_line_count, severity = match_context(context)
        if severity:
            for l in context[:-matched_line_count]:
                yield (None, None, l)  # todo: move to function and use yield from when moved to python3
            for l in context[-matched_line_count:]:
                yield (severity, rule_idx, l)
            context = []
        else:
            rule_idx, severity = match_line(line)
            if severity:
                for l in context[:-1]:
                    yield (None, None, l)
                yield (severity, rule_idx, line)
                context = []
    for line in context:
        yield (None, None, line)


def test_output():
    parser = argparse.ArgumentParser()
    parser.add_argument('severities', help='Which severities to reports, one chars for each: ewsn (n=none)')
    parser.add_argument('file', type=file, help='Build output to parse')
    args = parser.parse_args()
    for severity, rule_idx, line in parse_output_lines(args.file):
        ch = severity[0] if severity else 'n'
        if ch in args.severities:
            print '%s\t%s\t%s' % (severity or 'none', rule_idx if rule_idx is not None else '-', line.rstrip())

if __name__ == '__main__':
    test_output()
