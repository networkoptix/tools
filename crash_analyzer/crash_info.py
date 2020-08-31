#!/usr/bin/env python3

import hashlib
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

import dump_tool
import utils

logger = logging.getLogger(__name__)

# Suppress crazy amount of logs from network modules.
logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)

REPORT_NAME_REGEXP = re.compile(r'''
    (?P<binary> (?: (?!--). )+)
    --
    (?P<version> [0-9]+ \. [0-9]+ \. [0-9]+) \. (?P<build> [0-9]+)
        - (?P<changeset> [^-]+) (?P<customization> (?: -[^-]+)?) (?P<publication> (?: -[a-z_]+)?)
    --
    .* (?P<platform> (?: windows | linux | arm) - [a-z0-9]+) .*
    \.
    (?P<extension> [^\.]+)
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

        self.binary, version, self.build, self.changeset, customization, publication, \
            self.platform, self.extension = REPORT_NAME_REGEXP.match(name).groups()

        if len(self.extension) > 10:
            raise ReportNameError('Invalid extension in: ' + name)

        self.version = version[:-2] if version.endswith('.0') else version
        self.component = 'Server' if ('server' in self.binary) else 'Client'
        self.publication = publication[1:] if publication else 'public'

        self.customization = customization[1:] if customization else 'unknown'
        if self.customization == 'unknown' and self.version >= '2.4':
            raise ReportNameError('Customization is not specified: ' + name)

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

    def __init__(self, component: str, code: str, stack: List[str], full_stack: List[str]):
        self.component = component
        self.code = code
        self.stack = stack
        self.full_stack = full_stack

    def __repr__(self):
        return 'Reason({}, {}, {})'.format(repr(self.component), repr(self.code), repr(self.stack))

    def __str__(self):
        return '{}, code: {}, stack: {} frames, full_stack: {} frames, id: {}'.format(
            self.component, self.code, len(self.stack), len(self.full_stack), self.crash_id)

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


class ReportContent(ABC):
    def __init__(self, content: str):
        self._content = content.replace('\r', '')

    @property
    @abstractmethod
    def allow_not_own_stacks(self) -> bool:
        pass

    @abstractmethod
    def code(self) -> Optional[str]:
        pass

    @abstractmethod
    def stack(self) -> Optional[str]:
        pass

    @abstractmethod
    def is_new_line(self, line: str) -> bool:
        pass

    @abstractmethod
    def transform(self, line: str) -> Optional[str]:
        pass

    def _cut(self, begin: int, end: int, start=0, is_header=False) -> Optional[str]:
        try:
            start = self._content.index(begin, start) + len(begin)
            if is_header:
                start = self._content.index('\n', start) + 1

            stop = self._content.index(end or '\n', start)
            return self._content[start:stop]

        except (ValueError, IndexError):
            return None


def analyze_bt(report: Report, content: ReportContent) -> Reason:
    """Extracts error code and call stack by rules in describer.
    """
    logger.debug('Analyzing {} by {}'.format(report, content))

    code = content.code()
    if not code:
        raise AnalyzeError('Unable to get Error Code from: ' + report.name)

    stack_content = content.stack()
    if not stack_content:
        raise AnalyzeError('Unable to get Call Stack from: ' + report.name)

    original_stack = []
    for line in stack_content.splitlines():
        line = line.strip()
        if line:
            if content.is_new_line(line):
                original_stack.append(line)
            else:
                original_stack[-1] += ' ' + line

    transformed_stack = []
    for line in original_stack:
        transformed = content.transform(line)
        if transformed:
            transformed_stack.append(transformed)

    if not transformed_stack:
        raise AnalyzeError('No functions in Call Stack in: ' + report.name)

    is_own_values = [is_cxx_name_prefixed(x, report.component, *CXX_OWN_MODULE_PREFIXES)
                     for x in transformed_stack]

    if not any(is_own_values) and not content.allow_not_own_stacks:
        raise AnalyzeError('Entirely external stack in: ' + report.name)

    if is_own_values.count(True) < CXX_ONW_MODULES_MIN_COUNT:
        return Reason(report.component, code, transformed_stack, transformed_stack)

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

    return Reason(report.component, code, useful_stack, transformed_stack)


def analyze_linux_gdb_bt(report: Report, content: str, **options) -> Reason:
    """Extracts error code and call stack by rules from linux gdb bt output.
    """

    class GdbContent(ReportContent):
        # On some platforms only short function names are available,
        # so we can not understand if function is our own.
        allow_not_own_stacks = True

        def code(self) -> Optional[str]:
            return self._cut('Program terminated with signal ', '.')

        def stack(self) -> Optional[str]:
            return self._cut('Thread 1 ', '\n(gdb)', is_header=True)

        def is_new_line(self, line: str) -> bool:
            return any(line.startswith(p) for p in (
                '#',  # < Stack frame.
                'Backtrace stopped',  # < Error during unwind.
                '(More stack',  # < Truncation.
            ))

        def transform(self, line: str) -> Optional[str]:
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

    return analyze_bt(report, GdbContent(content))


def analyze_windows_cdb_bt(report: Report, content: str, **options) -> Reason:
    """Extracts error code and call stack by rules from windows cdb bt output.
    """

    class CdbContent(ReportContent):
        # If there are no our modules there is a good chance they are not able to be resolved.
        allow_not_own_stacks = False

        def code(self) -> Optional[str]:
            return self._cut('ExceptionCode: ', '\n')

        def stack(self) -> Optional[str]:
            try:
                # In case of pure virtual call windows shows breakpoint in main thread,
                # so we try to find required thread manually.
                start = self._content.rindex('Call Site', 0, self._content.index('_purecall'))
            except ValueError:
                start = 0

            return self._cut('Call Site', '\n\n', start, is_header=True)

        @staticmethod
        def is_new_line(line):
            # CDB newer uses the line wrap.
            return True

        @staticmethod
        def transform(line):
            # Keep only resolved symbols.
            module, *name = line.split(CXX_MODULE_SEPARATOR, 1)
            if not name:
                if module in ['ntdll', 'KERNELBASE']:
                    # This is very likely, that later stack frames resolution will be screwed up.
                    raise AnalyzeError('Unresolved system module {!r} in stack from: {}'.format(
                        module, report.name))
                return None

            # Replace lambdas from different builds with the same token.
            name = re.sub('<lambda_[0-9a-f]+>', '{lambda}', name[0])

            # Replace binary name with component so stacks from different
            # customizations are exactly the same.
            if module == report.binary:
                module = report.component

            return CXX_MODULE_SEPARATOR.join([module, remove_cxx_template_arguments(name)])

    return analyze_bt(report, CdbContent(content), **options)


class ProblemReports:
    def __init__(self, patterns: List[str]):
        self.patterns = list(p.split() for p in patterns)
        logger.debug('Problem builds patterns: {}'.format(self.patterns))

    def is_known(self, report: Report):
        for pattern in self.patterns:
            if all(part in report.name for part in pattern):
                return True

        return False


def analyze_reports_concurrent(reports: List[Report], problem_builds: list = [], **options) \
        -> List[Tuple[str, Reason]]:
    """Analyzes :reports in :directory, returns list of successful results.
    """
    known_problem_reports = ProblemReports(problem_builds)
    processed = []
    for report, result in zip(reports, utils.run_concurrent(analyze_report, reports, **options)):
        if isinstance(result, (
                Error, dump_tool.CdbError, dump_tool.DistError, UnicodeError, OSError)):
            if known_problem_reports.is_known(report):
                logger.debug(utils.format_error(result))
            else:
                logger.warning(utils.format_error(result))

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
