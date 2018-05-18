#!/usr/bin/env python3

import hashlib
import logging
import os
import re
from typing import List, Tuple

import dump_tool
import utils

logger = logging.getLogger(__name__)

# Suppress crazy amount of logs from network modules.
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)

REPORT_NAME_REGEXP = re.compile('''
    (?P<binary> (?: (?!--). )+)
    --
    (?P<version> [0-9]+ \. [0-9]+ \. [0-9]+) \. (?P<build> [0-9]+)
        - (?P<changeset> [^-]+) (?P<customization> (?: -[^-]+)?) (?P<beta> (?: -beta)?)
    --
    .+ \. (?P<extension> [^\.]+)
''', re.VERBOSE)

CXX_MODULE_SEPARATOR = '!'
CXX_LINUX_MODULE_RE = re.compile('.+lib(?P<name>[^\.\ ]+)\.so.*')

# Such hardcode looks awful and vary wrong, however these are essential rules for the stack
# extraction and it is not supposed to be changed ever!
# Also this crash monitor in bound to NX infrastructure in every way, so this make just one
# more binding point.
CXX_ONW_MODULES_MIN_COUNT = 3
CXX_OWN_MODULE_PREFIXES = [
    'nx_', 'nx::',  # < Modern module conventions.
    'Qn',  # < Legacy conventions.
    'udt',  # < Absorbed external code.
    'axiscamplugin', 'evidence_plugin', 'generic_multicast_plugin', 'generic_multicast_plugin',
    'image_library_plugin', 'it930x_plugin', 'mjpg_link', 'NxControl', 'quicksyncdecoder', 'rpi_cam',
    'xvbadecoder',  # < Legacy VMS server plugins.
]

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
    for prefix in prefixes:
        if line.startswith(prefix) or (CXX_MODULE_SEPARATOR + prefix) in line:
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

    is_own_values = [is_cxx_name_prefixed(x, report.component, *CXX_OWN_MODULE_PREFIXES)
                     for x in transformed_stack]

    if not any(is_own_values) and not describer.allow_not_own_stacks:
        raise AnalyzeError('Entirely external stack in: ' + report.name)

    if is_own_values.count(True) < CXX_ONW_MODULES_MIN_COUNT:
        return Reason(report.component, code, transformed_stack)

    useful_stack = []
    is_skipped = False
    for line, is_own in zip(transformed_stack, is_own_values):
        if is_own:
            if is_skipped:
                if useful_stack:
                    useful_stack.append('...')
                is_skipped = False
            useful_stack.append(line)
        else:
            is_skipped = True

    return Reason(report.component, code, useful_stack)


def analyze_linux_gdb_bt(report: Report, content: str, **options) -> Reason:
    """Extracts error code and call stack by rules from linux gdb bt output.
    """

    class GdbDescriber:
        code_begin = 'Program terminated with signal '
        code_end = '.'

        stack_begin = 'Thread 1 '
        stack_end = '\n(gdb)'

        # On some platforms only short function names are available, so we can not understand if function is own.
        allow_not_own_stacks = True

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
            module_match = CXX_LINUX_MODULE_RE.match(line)
            module_prefix = module_match.group('name') + CXX_MODULE_SEPARATOR if module_match else ''

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

            return module_prefix + transformed

    return analyze_bt(report, content, GdbDescriber)


def analyze_windows_cdb_bt(report: Report, content: str, **options) -> Reason:
    """Extracts error code and call stack by rules from windows cdb bt output.
    """

    class CdbDescriber:
        code_begin = 'ExceptionCode: '
        code_end = '\n'

        stack_begin = 'Call Site'
        stack_end = '\n\n'

        # If there are no our modules there is a good chance they are not able to be resolved.
        allow_not_own_stacks = False

        @staticmethod
        def is_new_line(line):
            # CDB newer uses the line wrap.
            return True

        @staticmethod
        def transform(line):
            # Keep only resolved symbols.
            module, *name = line.split(CXX_MODULE_SEPARATOR, 1)
            if not name:
                return None

            # Replace lambdas from different builds with the same token.
            name = re.sub('<lambda_[0-9a-f]+>', '{lambda}', name[0])

            # Replace binary name with component so stacks from different
            # customizations are exactly the same.
            if module == report.binary:
                module = report.component

            return CXX_MODULE_SEPARATOR.join([module, remove_cxx_template_arguments(name)])

    return analyze_bt(report, content, CdbDescriber, **options)


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

    logger.info('Successfully analyzed {} of {} report(s)'.format(len(processed), len(reports)))
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
