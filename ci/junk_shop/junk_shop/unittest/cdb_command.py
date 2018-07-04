"""
  junk_shop.unittest.cdb_command
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  Microsoft CDB.exe command wrapper to extract backtrace from windows DUMP file (.dmp) file.
  Used by junk_shop.unittest.platform. Based on devtools.crash_analyzer.dump_tool.
"""
import logging
# We're using subprocess32 Python3 backport to get communicate timeout feature.
# It'll be changed back to subprocess module after switching to Python3
from subprocess32 import Popen, TimeoutExpired, PIPE
import re


log = logging.getLogger(__name__)


CDB_EXE_PATH = r'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'

# Command set to get backtrace
# Please, see https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/using-debugger-commands
# to get help about CDB commands
CDB_COMMANDS = [
   b'.exr -1',  # Error
   b'.ecxr',    # Exception Context Record
   b'kc',       # Stack backtrace
   b'~*kc',     # Stack backtrace for all threads
   b'q'         # Exit
   ]

CDB_COMMAND_DESCRIPTIONS = [
    'Display error',
    'Display Exception Context Record',
    'Display stack backtrace',
    'Display stack backtrace for all threads'
    ]
# Regex to cut & change prompt lines
CDB_PROMPT_REGEX = r'^0:.*>'
CDB_PROCESS_TIMEOUT_SEC = 30


def process_cdb_output(output):
    """Change prompt lines to CDB command descriptions,
    or just remove prompt for `quit` command.
    """
    out_lines = []
    cmd_i = 0
    for line in output.split(b'\n'):
        if re.search(CDB_PROMPT_REGEX, line):
            if cmd_i < len(CDB_COMMAND_DESCRIPTIONS):
                out_lines.append(b'\n-- {} --\n'.format(CDB_COMMAND_DESCRIPTIONS[cmd_i]))
            cmd_i += 1
        else:
            out_lines.append(line)
    return b'\n'.join(out_lines)


def extract_backtrace_from_dump(dump_file, binary_path):
    """Returns a backtrace as a string for given ``dump_file``
    ``binary_path`` is using to get access to executable (.exe) and symbol (.pdb) files,
    required by CDB debugger.
    """
    cdb_command = [CDB_EXE_PATH, '-z', str(dump_file),
                   '-i', str(binary_path),
                   '-y', 'srv*;symsrv*;' + str(binary_path.parent)]
    try:
        cdb_process = Popen(
            cdb_command, stdin=PIPE, stdout=PIPE)
        stdout, _ = cdb_process.communicate(
            b'\n'.join(CDB_COMMANDS) + b'\n',
            timeout=CDB_PROCESS_TIMEOUT_SEC)
        return process_cdb_output(stdout)
    except TimeoutExpired:
        log.exception("Process '%r' process is timed out", cdb_command)
    except Exception as error:
        log.exception("Cannot execute '%r' exception: %s", cdb_command, error)
    return ''
