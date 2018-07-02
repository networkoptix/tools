import logging
import subprocess


log = logging.getLogger(__name__)


class CdbSession(object):
    """cdb.exe session to analyze DMP files."""

    CDB_PATH = r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'
    CDB_COMMANDS = [
        '.exr -1',  # Error
        '.ecxr',    # Context
        'kc',       # Error stack
        '~*kc'      # All threads stacks
     ]

    def __init__(self, dump_file, binary_path):
        self.shell = [self.CDB_PATH, '-z', str(dump_file),
                      '-i', str(binary_path),
                      '-y', 'srv*;symsrv*;' + str(binary_path.parent)]

    def get_backtrace(self):
        """Get backtrace: executes cdb commands and returns collected output."""
        out = ''
        try:
            cdb = subprocess.Popen(self.shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            for command in self.CDB_COMMANDS:
                cdb.stdin.write(command.encode() + b'\n')
                cdb.stdin.flush()
                while not out.endswith('\n0:'):
                    c = cdb.stdout.read(1)
                    if not c:
                        log.error("Cannot read dump file by command '%r'", self.shell)
                        return out
                    out += c
                # Skip all symbols before prompt
                while cdb.stdout.read(1) != b'>':
                    pass
                out += '\n'
            cdb.communicate(b'q\n')
        except Exception as error:
            log.error("Cannot execute '%r': %s", self.shell, error)
        return out
