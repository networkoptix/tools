#!/usr/bin/env python3

import hashlib
import logging
import os
import re
from typing import List, Tuple

import dump_tool
import utils

logger = logging.getLogger(__name__)

# Avoid crazy amount of logs from this module.
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)

REPORT_NAME_REGEXP = re.compile('''
    (?P<binary> (?: (?!--). )+)
    --
    (?P<version> [0-9]+ \. [0-9]+ \. [0-9]+) \. (?P<build> [0-9]+)
        - (?P<changeset> [^-]+) (?P<customization> (?: -[^-]+)?) (?P<beta> (?: -beta)?)
    --
    .+ \. (?P<extension> [^\.]+)
''', re.VERBOSE)


class Error(Exception):
    pass


class ReportNameError(Error):
    pass


class AnalyzeError(Error):
    pass


class Report:
    """Represents crash report by extracting metadata from it's name.
    """

    def __init__(self, name: str):
        self.name = os.path.basename(name)
        match = REPORT_NAME_REGEXP.match(name)
        if not match:
            raise ReportNameError('Unable to parse name: ' + self.name)

        self.binary, version, self.build, self.changeset, customization, beta, self.extension = \
            REPORT_NAME_REGEXP.match(name).groups()

        if customization:
            self.customization = customization[1:]
        else:
            self.customization = 'unknown'

        if len(self.extension) > 10:
            raise ReportNameError('Invalid extension in: ' + name)

        self.version = version[:-2] if version.endswith('.0') else version
        if self.customization == 'unknown' and self.version >= '2.4':
            raise ReportNameError('Customization is not specified: ' + name)

        self.component = 'Server' if ('server' in self.binary) else 'Client'
        if beta:
            self.beta = True

    def __repr__(self):
        return 'Report({})'.format(repr(self.name))

    def __str__(self):
        return self.name

    def __eq__(self, rhs):
        return self.name == rhs.name

    def file_mask(self) -> str:
        return self.name[:-len(self.extension)] + '*'


class Reason:
    """Represents unique crash reason. Several reports may produce the same reason.
    """

    def __init__(self, component: str, code: str, stack: List[str]):
        self.component = component
        self.code = code
        self.stack = stack

    def __repr__(self):
        return 'Reason({}, {}, {})'.format(repr(self.component), repr(self.code), repr(self.stack))

    def __str__(self):
        return '{}, code: {}, stack: {} frames, id: {}'.format(
            self.component, self.code, len(self.stack), self.crash_id)

    def __eq__(self, other):
        return self.component == other.component and \
               self.code == other.code and \
               self.stack == other.stack

    @property
    def crash_id(self) -> str:
        description = '\n\n'.join((self.component, self.code, '\n'.join(self.stack)))
        return hashlib.sha256(description.encode('utf-8')).hexdigest()


def analyze_bt(report: Report, content: str, describer: object) -> Reason:
    """Extracts error code and call stack by rules in describer.
    """
    logger.debug('Analyzing {} by {}'.format(report, describer.__name__))
    content = content.replace('\r', '')

    def cut(begin, end, is_header=False):
        try:
            start = content.index(begin) + len(begin)
            if is_header:
                start = content.index('\n', start) + 1

            stop = content.index(end or '\n', start)
            return content[start:stop]

        except (ValueError, IndexError):
            return None

    code = cut(describer.code_begin, describer.code_end)
    if not code:
        raise AnalyzeError('Unable to get Error Code from: ' + report.name)

    stack_content = cut(describer.stack_begin, describer.stack_end, True)
    if not stack_content:
        raise AnalyzeError('Unable to get Call Stack from: ' + report.name)

    stack = []
    for line in stack_content.splitlines():
        line = line.strip()
        if line:
            if describer.is_new_line(line):
                stack.append(line)
            else:
                stack[-1] += ' ' + line

    resolved_lines = 0
    transformed_stack = []
    for line in stack:
        line = describer.transform(line)
        transformed_stack.append(line)
        if describer.is_resolved(line):
            resolved_lines += 1

    if not resolved_lines:
        raise AnalyzeError('Unresolved Call Stack in: ' + report.name)

    return Reason(report.component, code, transformed_stack)


def analyze_linux_gdb_bt(report: Report, content: str) -> Reason:
    """Extracts error code and call stack by rules from linux gdb bt output.
    """

    class GdbDescriber:
        code_begin = 'Program terminated with signal '
        code_end = '.'

        stack_begin = 'Thread 1 '
        stack_end = '\n(gdb)'

        @staticmethod
        def is_new_line(line):
            return any(line.startswith(p) for p in (
                '#',  # < Stack frame.
                'Backtrace stopped',  # < Error during unwind.
                '(More stack',  # < Truncation.
            ))

        @staticmethod
        def transform(line):
            begin = 0
            while True:
                # Remove all argument values so stacks with different ones
                # are exactly the same.
                begin = line.find('=', begin) + 1
                if not begin:
                    return line

                end = line.find(',', begin)
                if end == -1:
                    end = line.find(')', begin)

                if end != -1:
                    line = line[:begin] + line[end:]

        @staticmethod
        def is_resolved(line):
            # Gdb replaces function names with ?? if they are not avaliable.
            return line.startswith('#') and line.find('??') == -1

    return analyze_bt(report, content, GdbDescriber)


def analyze_windows_cdb_bt(report: Report, content: str) -> Reason:
    """Extracts error code and call stack by rules from windows cdb bt output.
    """

    class CdbDescriber:
        code_begin = 'ExceptionCode: '
        code_end = '\n'

        stack_begin = 'Call Site'
        stack_end = '\n\n'

        @staticmethod
        def is_new_line(line):
            # CDB newer uses the line wrap.
            return True

        @staticmethod
        def transform(line):
            if line.startswith(report.binary + '!'):
                # Replace binary name with component so stacks from different
                # customizations are exactly the same.
                return report.component + line[len(report.binary):]

            return line

        @staticmethod
        def is_resolved(line):
            module, *name = line.split('!')
            if not any(module.startswith(x) for x in (report.component, 'nx_')):
                return False  # < We expect some of our modules to be resolved.

            return bool(name)  # < Function name is present.

    return analyze_bt(report, content, CdbDescriber)


def analyze_reports_concurrent(reports: List[Report], **options) -> List[Tuple[str, Reason]]:
    """Analyzes :reports in :directory, returns list of successful results.
    """
    processed = []
    for report, result in zip(reports, utils.run_concurrent(analyze_report, reports, **options)):
        if isinstance(result, (Error, dump_tool.CdbError, dump_tool.DistError)):
            logger.warning(utils.format_error(result))
        elif isinstance(result, Exception):
            logger.error(utils.format_error(result))
        else:
            processed.append((report, result))

    logger.info('Successfully analyzed {} reports'.format(len(processed)))
    return processed


def analyze_report(report: Report, directory: utils.Directory, **dump_tool_options) -> Reason:
    report_file = directory.file(report.name)
    if report.extension == 'gdb-bt':
        return analyze_linux_gdb_bt(report, report_file.read_string())

    if report.extension == 'cdb-bt':
        return analyze_windows_cdb_bt(report, report_file.read_string())

    if report.extension == 'dmp':
        content = dump_tool.analyse_dump(dump_path=report_file.path, **dump_tool_options)
        return analyze_windows_cdb_bt(report, content)

    raise NotImplemented('Dump format is not supported: ' + report.name)
