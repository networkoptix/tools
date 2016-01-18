__author__ = 'Danil Lavrentyuk'

CHECK_PERIOD = 60 # seconds
PROCESS_NAME = "crashmon"

CRASH_LIST_URL = "http://stats.networkoptix.com/crashserver/api/list?extension={0}"
DUMP_BASE = "http://stats.networkoptix.com/crash_dumps/"

CRASH_EXT = ('crash', 'gdb-bt')
AUTH = ("statlord", "razdvatri")

LASTS_FILE = "last_crash.py" #

def crash_list_url(ext):
    return CRASH_LIST_URL.format(ext)

LAST_CRASH_TIME_TPL = """# Last crashfile timestamps
# Maintained automaticaly. Edit if you really know what do you do only!
%name = %r
"""
