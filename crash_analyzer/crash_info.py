#!/usr/bin/env python

class Error(Exception):
    pass

class Description(object):
    def __init__(self, name):
        '''Created dump description by it's canonical name:
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

    def describe_bt(self, content, describer):
        '''Extracts error code and call stack by rules in describer.
        '''
        def cut(content, begin, end, is_header=False):
            content = content.replace('\r', '')
            try:
                start = content.index(begin) + len(begin)
                if is_header:
                    start = content.index('\n', start) + 1

                stop = content.index(end or '\n', start)
                return content[start:stop]

            except ValueError, IndexError:
                return None

        self.code = cut(content, describer.code_begin, describer.code_end)
        if not self.code:
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

        self.stack = transformed_stack
        return self.code, self.stack

    def describe_linux_gdb_bt(self, content):
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

        return self.describe_bt(content, GdbDescriber)

    def describe_windows_cdb_bt(self, content):
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

        return self.describe_bt(content, CdbDescriber)

