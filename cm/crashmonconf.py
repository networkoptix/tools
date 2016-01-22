__author__ = 'Danil Lavrentyuk'

CHECK_PERIOD = 1 # minutes
SUMMARY_PERIOD = 7 # days!
PROCESS_NAME = "crashmon"

CRASH_LIST_URL = "http://stats.networkoptix.com/crashserver/api/list?extension={0}"
DUMP_BASE = "http://stats.networkoptix.com/crash_dumps"

CRASH_EXT = ('crash', 'gdb-bt')
AUTH = ("statlord", "razdvatri")

LASTS_FILE = "last_crash.py" #
KNOWN_FALTS_FILE = "known-faults.list"

def crash_list_url(ext):
    return CRASH_LIST_URL.format(ext)

LAST_CRASH_TIME_TPL = """# Last crashfile timestamps
# Maintained automaticaly. Edit if you really know what do you do only!
%s = %r
%s = %d
"""

SMTP_ADDR = 'smtp.gmail.com:587'
SMTP_LOGIN = 'service@networkoptix.com'
SMTP_PASS = 'kbnUk06boqBkwU'

MAIL_FROM = '"Crash Monitor" <crashmon@networkoptix.com>'
MAIL_TO = 'crashdumps@networkoptix.com'
MAIL_TO = 'dlavrentyuk@networkoptix.com'
