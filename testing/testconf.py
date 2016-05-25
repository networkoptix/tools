# -*- coding: utf-8 -*-
__author__ = 'Danil Lavrentyuk'
"""
The main configuration file for autotest scripts.
Note, this file is just an initial values source for the main script,
which could (and will) modify some values according to command line options
and an environment.
So if you import it from other modules, don't use it's values before the main script
fixes them (see set_paths and set_branches methods in auto.py).
"""
import os.path

DEBUG = True

TEMP = '' # temporary files directory, leave it '' for the process' current directory
# FIXME check if it's used where it should be!

PROJECT_ROOT = "~/develop/nx_vms"

UT_SUBDIR = "unit_tests" # ut sources subdirectory, relative to PROJECT_ROOT

FAIL_FILE = './fails.py' # where to save failed branches list
RESTART_FLAG = './.restart'
STOP_FLAG = './.stop'
RESTART_BY_EXEC = True

BUILD_CONF_SUBPATH = os.path.join("build_variables", "target", "current_config.py")
BUILD_CONF_PATH = ''

HG_CHECK_PERIOD = 5 * 60 # seconds, complete check period, including time consumed by check, builds and tests
MIN_SLEEP = 60 # seconds, minimal sleep time after one perform before another
UT_PIPE_TIMEOUT = 100 * 1000  # milliseconds. Unit tests' pipe timeout
FT_PIPE_TIMEOUT = 90 * 1000  # ... Functional tests' pipe timeout
UT_TIME_LIMIT = 10 * 60 # Maximum time for each one unittest to run.
TEST_TERMINATION_WAIT = 7 # seconds, how long to wait for test process teermination before kill it
BUILD_LOG_LINES = 250 # How may last lines are saved to report build process failure
FUNCTEST_LAST_LINES = 50 # Lines to show if the functional tests hang.
MVN_TERMINATION_WAIT = 15 # seconds, how long to wait for mvn return code
MVN_BUFFER = 50000        # maven output pipe buffer size
MVN_THREADS = 8 # Number of threads to be used by maven (mvn -T)
SELF_RESTART_TIMEOUT = 10 # seconds
SLEEP_AFTER_BOX_START = 1 # seconds

ULIMIT_NOFILE_REQUIRED = 4096

# Multiple branches example: BRANCHES = ('dev_2.4.0', 'dev_2.5', 'dev_2.4.0_gui')
#  do not use '.' here except it is the only branch you check
BRANCHES = ('dev_2.5',)
TESTS = ('common_ut', 'mediaserver_core_ut', 'client_ut') # unit tests' binary files names

SMTP_ADDR = 'smtp.gmail.com:587'
SMTP_LOGIN = 'service@networkoptix.com'
SMTP_PASS = 'kbnUk06boqBkwU'


MAIL_FROM = '"AutoTest System" <autotest@networkoptix.com>'
MAIL_TO = 'test-results@networkoptix.com'
BRANCH_CC_TO = dict() # additional addresses per branch

#TODO
ALERT_TO = 'dlavrentyuk@networkoptix.com' # to send mail about check process fails (such as hg call fails)

#############################################

HG = "/usr/bin/hg"
MVN = "/home/danil/develop/buildenv/maven/bin/mvn"
VAGRANT = "/usr/bin/vagrant"

VAG_DIR = "./vagrant"

HG_IN = [HG, "incoming", "--quiet", "--template={branch},"]
HG_REVLIST = [HG, "incoming", "--quiet", "--template={branch};{author};{node|short};{date|isodatesec};{desc|tabindent}\n"]
HG_PULL = [HG, "pull", "--quiet"]
HG_UP = [HG, "update"]
HG_PURGE = [HG, "purge", "--all"]
HG_BRANCH = [HG, "branch"]

VAGR_DESTROY = [VAGRANT, "destroy", "-f"]
VAGR_RUN = [VAGRANT, "up"]
VAGR_STOP = [VAGRANT, "halt"]
VAGR_STAT = [VAGRANT, "status"]

MVN_BUILD_CONFIG = 'release'
TEST_CAMERA_SUBPATH = "build_environment/target/bin/%s/testcamera" % MVN_BUILD_CONFIG

BOX_NAMES = {
    "Box1": "box1",
    "Box2": "box2",
    "Nat": "nat",
    "Behind": "behind",
}

BOX_IP = { # IPs to check if mediaserver is up after a box goes up (boxes without mediaserver are skipped
    'Box1': '192.168.109.8',
    'Box2': '192.168.109.9',
    'Nat': '192.168.109.10',
    'Behind': '192.168.110.3',
}

CHECK_BOX_UP = frozenset(['Box1', 'Box2', 'Behind'])

BOX_POST_START = {
    'Behind': 'post-create-behind-nat.sh'
}

BOXES_NAMES_FILE = os.path.join(VAG_DIR, 'boxes.rb')

MEDIASERVER_PORT = 7001
MEDIASERVER_USER = 'admin'
MEDIASERVER_PASS = 'admin'

START_CHECK_TIMEOUT = 30 # seconds
ALL_START_TIMEOUT_BASE = 120 # seconds, per server

SKIP_TESTS = {
# 'branch_label' : {...names...} (!!! it should be set or frozenset)
# possible test names:
#   all names from TESTS list
#   'all_ut' - all unit tests completly
#   'time' - to skip time synchronization test
#   'backup' - to skip backup storage test
#   'msarch' - to skip nultiserver archive test
#   'natcon' - to skip connection behind NAT test
#   'proxy' - to skip server proxy test
}

# Skip these test for all branches
SKIP_ALL = set() # {'msarch'}

SUDO_REQUIRED = set(('mediaserver_core_ut',))  # set of unittests that require sudo to call

SUBPROC_ARGS = dict(universal_newlines=True, cwd=PROJECT_ROOT, shell=False)

#------------------------------------------------------------------

try:
    import testconf_local # we need itself to access it's file name
    from testconf_local import *
except ImportError:
    pass
