#!/usr/bin/env python3

import hashlib
import os

from typing import List, Tuple

class Error(Exception):
    pass

class Reason(object):
    def __init__(self, component: str, code: str, stack: List[str]):
        self.component = component
        self.code = code
        self.stack = stack

    def __str__(self):
        return '{}, code: {}, stack: {} frames'.format(self.component, self.code, len(self.stack))

    def crash_id(self) -> str:
        return hashlib.sha256('\n\n'.join(self.component, self.code, '\n'.join(self.stack)))

class Report(object):
    def __init__(self, name: str):
        '''Created crash report description by it's canonical name:
           <binary>--<version>.<build>-<changeset>-<customization>--<etc>.<format>
        '''
        def component(string):
            return 'Server' if ('server' in string) else 'Client'

        def team(string):
            return 'Server' if ('server' in string) else 'GUI'

        def format(string):
            return string.split('.')[-1:][0]

        def set_version_info(string):
            split = string.split('.')
            self.build = split[3]
            self.version = split[0] + '.' + split[1]
            if split[2] != '0':
                self.version += '.' + split[2]

        def set_build_info(string):
            split = string.split('-')
            self.changeset = split[1]
            self.customization = split[2]
            set_version_info(split[0])
            if split[3:] == ['beta']:
                self.beta = True

        split = name.split('--')
        try:
            self.name = name
            self.binary = split[0]
            self.component = component(split[0])
            self.team = team(split[0])
            self.format = format(split[-1])
            set_build_info(split[1])

        except IndexError:
            raise Error('Unable to parse name: ' + self.name)

        if len(self.format) > 10:
            raise Error('Invalid format: ' + self.format)

    def __str__(self):
        return self.name

    def analyze_bt(self, content: str, describer: object) -> Reason:
        '''Extracts error code and call stack by rules in describer.
        '''
        def cut(content, begin, end, is_header = False):
            content = content.replace('\r', '')
            try:
                start = content.index(begin) + len(begin)
                if is_header:
                    start = content.index('\n', start) + 1

                stop = content.index(end or '\n', start)
                return content[start:stop]

            except (ValueError, IndexError):
                return None

        code = cut(content, describer.code_begin, describer.code_end)
        if not code:
            raise Error('Unable to get Error Code for: ' + self.name)

        stack_content = cut(content, describer.stack_begin, describer.stack_end, True)
        if not stack_content:
            raise Error('Unable to get Call Stack for: ' + self.name)

        stack = []
        for line in stack_content.split('\n'):
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
            raise Error('Unresolved Call Stack for: ' + self.name)

        return Reason(self.component, code, transformed_stack)

    def analyze_linux_gdb_bt(self, content: str) -> Reason:
        '''Extracts error code and call stack by rules from linux gdb bt output.
        '''
        class GdbDescriber:
            code_begin = 'Program terminated with signal '
            code_end = '.'

            stack_begin = 'Thread 1 '
            stack_end = '\n(gdb)'

            @staticmethod
            def is_new_line(line):
                return any(line.startswith(p) for p in (
                    '#', #< Stack frame.
                    'Backtrace stopped', #< Error during unwind.
                    '(More stack' #< Trancation.
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

        return self.analyze_bt(content, GdbDescriber)

    def analyze_windows_cdb_bt(self, content: str) -> Reason:
        '''Extracts error code and call stack by rules from windows cdb bt output.
        '''
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
                if line.startswith(self.binary + '!'):
                    # Replace binary name with component so stacks from different
                    # customizations are exactly the same.
                    return self.component + line[len(self.binary):]

                return line

            @staticmethod
            def is_resolved(line):
                split = line.split('!')
                if not any(split[0].startswith(x) for x in (self.component, 'nx_')):
                    return False #< We expect some of our modules to be resolved.

                return len(split) > 1 #< Function name is present.

        return self.analyze_bt(content, CdbDescriber)

    def crash_id(self):
        '''Generates error code and stack based crash id to find similar cases.
        '''
        return hashlib.sha256(self.code + '\n\n' + '\n'.join(self.stack))


def analyze(report_path: str) -> Tuple[Report, Reason]:
    '''Describes report by file name and it's format.
    '''
    report = Report(os.path.basename(report_path))
    report.files = [report_path]
    with open(report_path, 'r') as f:
        content = f.read()

    if report.format == 'gdb-bt':
        reason = report.analyze_linux_gdb_bt(content)

    elif report.format == 'cdb-bt':
        reason = report.analyze_windows_cdb_bt(content)

    # TODO: Add support for dmp.
    else:
        raise Error('Dump format is not supported: ' + report_path)

    return report, reason
