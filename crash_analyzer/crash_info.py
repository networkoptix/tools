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

    @property
    def full_version(self) -> str:
        version_numbers = self.version.split('.') + ['0']
        return '.'.join(version_numbers[:3] + [self.build])

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


def remove_cxx_template_arguments(line):
    while True:
        start = line.find('<')
        if start == -1:
            return line

        current = start + 1
        opened = 1
        while opened:
            if current >= len(line):
                return line[:start]
            if line[current] == '<':
                opened += 1
            if line[current] == '>':
                opened -= 1
            current += 1

        line = line[:start] + line[current:]


def is_cxx_name_prefixed(line, *prefixes):
    name = ' ' + line
    for prefix in prefixes:
        if ' ' + prefix in name:
            return True

    return False


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

    original_stack = []
    for line in stack_content.splitlines():
        line = line.strip()
        if line:
            if describer.is_new_line(line):
                original_stack.append(line)
            else:
                original_stack[-1] += ' ' + line

    transformed_stack = []
    for line in original_stack:
        transformed = describer.transform(line)
        if transformed:
            transformed_stack.append(transformed)

    if not transformed_stack:
        raise AnalyzeError('No functions in Call Stack in: ' + report.name)

    is_useful = [describer.is_useful(x) for x in transformed_stack]
    is_useful_count = is_useful.count(True)
    if not is_useful_count:
        if describer.allow_not_useful_stacks:
            return Reason(report.component, code, transformed_stack)
        raise AnalyzeError('Not useful Call Stack in: ' + report.name)

    if is_useful_count < 3:
        return Reason(report.component, code, transformed_stack)

    useful_stack = []
    is_skipped = False
    for line, is_useful in zip(transformed_stack, is_useful):
        if is_useful:
            if is_skipped:
                if useful_stack:
                    useful_stack.append('...')
                is_skipped = False
            useful_stack.append(line)
        else:
            is_skipped = True

    return Reason(report.component, code, useful_stack)


_NX_OBJECT_NAME_PREFIXES = [
    'nx::',
    'nx_',
    'Qn',
    'CUDT',
]


def analyze_linux_gdb_bt(report: Report, content: str) -> Reason:
    """Extracts error code and call stack by rules from linux gdb bt output.
    """

    class GdbDescriber:
        code_begin = 'Program terminated with signal '
        code_end = '.'

        stack_begin = 'Thread 1 '
        stack_end = '\n(gdb)'

        allow_not_useful_stacks = True

        @staticmethod
        def is_new_line(line):
            return any(line.startswith(p) for p in (
                '#',  # < Stack frame.
                'Backtrace stopped',  # < Error during unwind.
                '(More stack',  # < Truncation.
            ))

        @staticmethod
        def transform(line):
            transformed = remove_cxx_template_arguments(line)

            # Remove arguments and other details.
            call_position = transformed.find('(')
            if call_position == -1:
                return None
            transformed = transformed[:call_position]

            # Remove frame number.
            frame_position = transformed.find(' ')
            if frame_position == -1 or not transformed.startswith('#'):
                return None
            transformed = transformed[frame_position:]

            # Remove address if present.
            in_position = transformed.find(' in ')
            if in_position != -1:
                transformed = transformed[in_position + 4:]
            transformed = transformed.strip()

            # Remove return type.
            return_type_end = transformed.find(' ') + 1
            if return_type_end:
                transformed = transformed[return_type_end:]

            # Remove optimized out trash.
            if transformed == '??':
                return None

            return transformed

        @staticmethod
        def is_useful(line):
            return is_cxx_name_prefixed(line, *_NX_OBJECT_NAME_PREFIXES)

    return analyze_bt(report, content, GdbDescriber)


def analyze_windows_cdb_bt(report: Report, content: str) -> Reason:
    """Extracts error code and call stack by rules from windows cdb bt output.
    """

    class CdbDescriber:
        code_begin = 'ExceptionCode: '
        code_end = '\n'

        stack_begin = 'Call Site'
        stack_end = '\n\n'

        allow_not_useful_stacks = False

        @staticmethod
        def is_new_line(line):
            # CDB newer uses the line wrap.
            return True

        @staticmethod
        def transform(line):
            if line == '0x0':
                return None

            # Replace lambdas from different builds with the same token.
            line = re.sub('<lambda_[0-9a-f]+>', '{lambda}', line)

            # Replace binary name with component so stacks from different
            # customizations are exactly the same.
            if line.startswith(report.binary + '!'):
                line = report.component + line[len(report.binary):]

            return remove_cxx_template_arguments(line)

        @staticmethod
        def is_useful(line):
            module, *name = line.split('!')
            if not name:
                return False  # < Function name is not present.

            if module == report.component or module.startswith('nx_') or \
                    is_cxx_name_prefixed(name[0], *_NX_OBJECT_NAME_PREFIXES):
                return True  # < NX Component.

            return False

    return analyze_bt(report, content, CdbDescriber)


def analyze_reports_concurrent(reports: List[Report], problem_versions: list = [], **options) \
        -> List[Tuple[str, Reason]]:
    """Analyzes :reports in :directory, returns list of successful results.
    """
    problem_versions = set(problem_versions)
    processed = []
    for report, result in zip(reports, utils.run_concurrent(analyze_report, reports, **options)):
        if isinstance(result, (Error, dump_tool.CdbError, dump_tool.DistError)):
            if report.full_version in problem_versions:
                logger.debug(utils.format_error(result))
            else:
                logger.warning(utils.format_error(result))
                problem_versions.add(report.full_version)
        elif isinstance(result, Exception):
            logger.error(utils.format_error(result))
        else:
            processed.append((report, result))

    logger.info('Successfully analyzed {} of {} reports'.format(len(processed), len(reports)))
    return processed


def analyze_report(report: Report, directory: utils.Directory, **dump_tool_options) -> Reason:
    report_file = directory.file(report.name)
    if report.extension == 'gdb-bt':
        return analyze_linux_gdb_bt(report, report_file.read_string())

    if report.extension == 'cdb-bt':
        return analyze_windows_cdb_bt(report, report_file.read_string())

    if report.extension == 'dmp':
        content = dump_tool.analyse_dump(
            dump_path=report_file.path, customization=report.customization, **dump_tool_options)
        return analyze_windows_cdb_bt(report, content)

    raise NotImplementedError('Dump format is not supported: ' + report.name)
