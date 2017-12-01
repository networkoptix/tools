# unit test platform support

import logging
import abc
import sys
import os
import os.path
import re
import subprocess
import signal

log = logging.getLogger(__name__)


class Platform(object):

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def abort_process(self, process):
        pass

    @abc.abstractmethod
    def do_unittests_pre_checks(self):
        pass

    def env_with_library_path(self, config):
        library_path_list = self.platform_library_path(config)
        path_var = self.library_path_var
        if path_var in os.environ:
            library_path_list = os.environ[path_var].split(os.pathsep) + library_path_list
        env = os.environ.copy()
        env[self.library_path_var] = os.pathsep.join(filter(None, library_path_list))
        return env

    @abc.abstractproperty
    def library_path_var(self):
        pass

    @abc.abstractmethod
    def platform_library_path(self, config):
        pass

    @abc.abstractmethod
    def extract_core_source_binary(self, core_path):
        pass

    @abc.abstractmethod
    def extract_core_backtrace(self, binary_path, core_path):
        pass


class WindowsPlatform(Platform):

    def abort_process(self, process):
        process.kill()
    
    def do_unittests_pre_checks(self):
        return []

    @property
    def library_path_var(self):
        return 'PATH'

    def platform_library_path(self, config):
        return [os.path.join(config['QT_DIR'], 'bin'), config['BIN_PATH']]

    def extract_core_source_binary(self, core_path):
        return None

    def extract_core_backtrace(self, binary_path, core_path):
        return None


class PosixPlatform(Platform):

    __metaclass__ = abc.ABCMeta

    def abort_process(self, process):
        process.send_signal(signal.SIGABRT)  # using signal producing core dump

    def do_unittests_pre_checks(self):
        error_list = [
            self.check_debugger_exists(),
            self.check_core_pattern(),
            self.check_ulimit_core(),
            ]
        return filter(None, error_list)

    @abc.abstractproperty
    def expected_core_pattern(self):
        return None

    @abc.abstractmethod
    def read_core_pattern(self):
        pass

    @abc.abstractmethod
    def check_debugger_exists(self):
        pass

    def check_core_pattern(self):
        core_pattern = self.read_core_pattern()
        if core_pattern is not None and core_pattern != self.expected_core_pattern:
            return ('Core pattern is %r, but expected is %r; core files will not be collected.' %
                    (core_pattern, self.expected_core_pattern))

    def check_ulimit_core(self):
        core_ulimit = subprocess.check_output('ulimit -c', shell=True).rstrip()
        if core_ulimit != 'unlimited':
            return 'ulimit for core files is %s, but expected is "unlimited"; core files may not be generated.' % core_ulimit

    def platform_library_path(self, config):
        return [config['QT_LIB'], config['LIB_PATH']]

    def which(self, prog_name):
        try:
            return subprocess.check_output(['which', prog_name]).rstrip()
        except subprocess.CalledProcessError as x:
            return None


class LinuxPlatform(PosixPlatform):

    CORE_PATTERH_FILE = '/proc/sys/kernel/core_pattern'

    GDB_BACKTRACE_EXTRACT_COMMANDS = [
        r'set print static-members off',
        r'echo \n-- current thread backtrace --\n',
        r'bt',
        r'echo \n-- thread list --\n',
        r'info threads',
        r'echo \n-- backtraces of all threads --\n',
        r'thread apply all backtrace',
        r'echo \n-- full backtraces of all threads --\n',
        r'thread apply all backtrace full',
        ]

    def __init__(self):
        self._gdb_path = self.which('gdb')
        file_ver = self.get_file_utility_version()
        self._is_file_utility_old = file_ver <= (5, 14)
        if self._is_file_utility_old:
            log.warning('"file" utility it too old: %s, does not support -P argument', '.'.join(map(str, file_ver)))

    @property
    def expected_core_pattern(self):
        return '%e.core.%t.%p'

    def read_core_pattern(self):
        with file(self.CORE_PATTERH_FILE) as f:
            return f.read().strip()

    def check_debugger_exists(self):
        if not self._gdb_path:
            return 'gdb is missing: core files will not be parsed'

    @property
    def library_path_var(self):
        return 'LD_LIBRARY_PATH'

    def extract_core_source_binary(self, core_path):
        if self._is_file_utility_old:
            phnum_args = []
        else:
            phnum_args = ['-Pelf_phnum=10000']
        try:
            # max ELF program sections processed, will get 'too many program headers' message overwise:
            output = subprocess.check_output(['file'] + phnum_args + [core_path], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as x:
            log.warning('Error extracting core file source binary from %s: %s', core_path, x)
            log.warning('%s', x.output)
            return None
        mo = re.match(r".*, from '(\S+).*'", output.rstrip())
        if not mo:
            log.warning('Error extracting core file source binary from %s: none returned', core_path)
            return None
        return mo.group(1)

    def extract_core_backtrace(self, binary_path, core_path):
        if not binary_path: return
        log.info('Extracting core file backtrace from %s, generated by %s', core_path, binary_path)
        args = [self._gdb_path, '--quiet', '--batch', binary_path, core_path]
        for command in self.GDB_BACKTRACE_EXTRACT_COMMANDS:
            args += ['-ex', command]
        return subprocess.check_output(args, stderr=subprocess.STDOUT)

    def get_file_utility_version(self):
        output = subprocess.check_output(['file', '-v'])  # 'file-5.14'
        return tuple(map(int, output.splitlines()[0].split('-')[1].split('.')))


class DarwinPlatform(PosixPlatform):

    LLDB_BACKTRACE_EXTRACT_COMMANDS = [
        r'script print "\n-- current thread backtrace --\n"',
        r'thread backtrace',
        r'script print "\n-- thread list --\n"',
        r'thread list',
        r'script print "\n-- backtraces of all threads --\n"',
        r'thread backtrace all',
        ]

    def __init__(self):
        self._lldb_path = self.which('lldb')

    @property
    def expected_core_pattern(self):
        return '%N.core.%P'  # N: process name, P: pid

    def read_core_pattern(self):
        line = subprocess.check_output(['sysctl', 'kern.corefile']).rstrip()
        return line.split(': ')[1]

    def check_debugger_exists(self):
        if not self._lldb_path:
            return 'lldb is missing: core files will not be parsed'

    @property
    def library_path_var(self):
        return 'DYLD_LIBRARY_PATH'

    def extract_core_source_binary(self, core_path):
        try:
            args = [self._lldb_path, '--batch', '-c', core_path, '-o', 'target list']
            log.debug('Extracting core file source with command: %s', subprocess.list2cmdline(args))
            output = subprocess.check_output(args, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as x:
            log.warning('Error extracting core file source binary from %s: %s', core_path, x)
            log.warning('%s', x.output)
            return None
        mo = re.search(r'^\* target #0: (\S+)', output.rstrip(), re.MULTILINE)
        if not mo:
            log.warning('Error extracting core file source binary from %s: none returned', core_path)
            return None
        return mo.group(1)

    def extract_core_backtrace(self, binary_path, core_path):
        log.info('Extracting core file backtrace from %s, generated by %s', core_path, binary_path or 'unknown binary')
        args = ([self._lldb_path, '--batch', '--core', core_path] +
                ['--one-line=%s' % command for command in self.LLDB_BACKTRACE_EXTRACT_COMMANDS])
        log.debug('Extracting core file backtrace with command: %s', subprocess.list2cmdline(args))
        return subprocess.check_output(args, stderr=subprocess.STDOUT)


def create_platform():
    if sys.platform == 'linux2':
        return LinuxPlatform()
    if sys.platform == 'darwin':
        return DarwinPlatform()
    if sys.platform == 'win32':
        return WindowsPlatform()
    assert False, 'Unknown platform: %r' % sys.platform
