__author__ = 'Danil Lavrentyuk'

CHECK_PERIOD = 1 # minutes, used with -a command line option
SUMMARY_PERIOD = 7 # days!
PROCESS_NAME = "crashmon"

CRASH_LIST_URL = "http://stats.networkoptix.com/crashserver/api/list?extension={0}"
DUMP_BASE = "http://stats.networkoptix.com/crash_dumps"

AUTH = ("statlord", "razdvatri")

# the last relese build per branch (builds after that number are hotfixes for that branch)
# it's important to configure this dict for every released version so
# that closed bugs for this version reopen, if reappear in hotfix builds,
# but not reopen if appear in earlier builds (i.e. in release)
RELEASE_BUILDS = {
    # (x, y, z) => build, where all values are ints
    (2, 5, 0): 11500,
}

LASTS_FILE = "last-crash" #
KNOWN_FAULTS_FILE = "known-faults.list"

ISSUE_LEVEL = [ # pairs of crash number  to set and priority name
    #[3, "Low"],
    [3, "Medium"],
    [10, "High"],
    #[20, "Highest"]
]

MAX_ATTACHMENTS = 10

SEND_NEW_CRASHES = True # send an email for each new crash trace ptath or not?

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

MAIL_FROM = '"Crash Monitor (local)" <crashmon@networkoptix.com>'
MAIL_TO = 'crashdumps@networkoptix.com'
MAIL_TO = 'dlavrentyuk@networkoptix.com'
