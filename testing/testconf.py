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

UT_SUBDIR = "unit_tests"  # ut sources subdirectory, relative to PROJECT_ROOT
FT_PATH = "$NX/func_tests"  # if it starts with $NX, set_paths() will update it with PROJECT_ROOT used

FAIL_FILE = './fails.py' # where to save failed branches list
RESTART_FLAG = './.restart'
STOP_FLAG = './.stop'
RESTART_BY_EXEC = True

# Usage of UT_TEMP_DIR: leading '/' means abs.path, leading './' rel.path based on the script's dir,
# otherwise it's a rel.path based on PROJECT_ROOT
# it shouldn't be any common 'temporary' directory itself, but could be a subdirectory there
# also you can end path with '$' which will make the script to add it's PID to the path
# instead of '$'
# Never should two or more processes of the script share the same UT_TEMP_DIR since both of them
# clear it before starting of any unittest (usage of PID helps here).
UT_TEMP_DIR = '/var/tmp/autotest.$'
UT_TEMP_DIR_PID_USED = True  # it realy doesn't matter since set_paths() set the correct value here
UT_TEMP_DIR_SAFE = False  # set it to False if don't use PID and UT_TEMP_DIR points to some common directory
                          # if it's True, script will clear it contents even if PID not used
UT_BRANCHES_NO_TEMP = set(('dev_2.5', 'prod_2.5'))  # what branches don't use --tmp for unittests

BUILD_CONF_SUBPATH = os.path.join("build_variables", "target", "current_config.py")
BUILD_CONF_PATH = ''

HG_CHECK_PERIOD = 5 * 60 # seconds, complete check period, including time consumed by check, builds and tests
MIN_SLEEP = 60 # seconds, minimal sleep time after one perform before another
UT_PIPE_TIMEOUT = 100 * 1000  # milliseconds. Unit tests' pipe timeout
FT_PIPE_TIMEOUT = 90 * 1000  # ... Functional tests' pipe timeout
UT_TIME_LIMIT = 10 * 60  # Maximum time for each one unittest to run.
TEST_TERMINATION_WAIT = 7  # seconds, how long to wait for test process teermination before kill it
BUILD_LOG_LINES = 500  # How may last lines are saved to report build process failure
MAX_LOG_NO_ATTACH = 50  #  If log is longer, send it in an attachment
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

SMTP_ADDR = 'email-smtp.us-east-1.amazonaws.com:587'
SMTP_LOGIN = 'AKIAJ6MLW7ZT7WXXXOIA' # service@networkoptix.com
SMTP_PASS = 'AlYDnddPk8mWorQFVogh8sqkQX6Nv01JwxxfMoYJAFeC'


MAIL_FROM = '"AutoTest System" <autotest@networkoptix.com>'
MAIL_TO = 'test-results@networkoptix.com'
BRANCH_CC_TO = dict() # additional addresses per branch

#TODO
ALERT_TO = 'dlavrentyuk@networkoptix.com' # to send mail about check process fails (such as hg call fails)

#############################################

HG = "/usr/bin/hg"
MVN = "/home/danil/develop/buildenv/maven/bin/mvn"
VAGRANT = "/usr/bin/vagrant"
SUDO = "/usr/bin/sudo"
RM = "/bin/rm"
DOCKER = "/usr/bin/docker"

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
VAGR_SSHCONF = [VAGRANT, "ssh-config"]

MVN_BUILD_CONFIG = 'release'
TEST_CAMERA_SUBPATH = "build_environment/target/bin/%s/testcamera" % MVN_BUILD_CONFIG

# docker usage options
UT_USE_DOCKER = False  # use diocker container for unittests
DOCKER_REGISTRY = "la.hdw.mx:5000"
DOCKER_IMAGE_NAME = "la.hdw.mx:5000/nxvms-ut:latest"
#DOCKER_CONTAINER_NAME = "ut"
DOCKER_COPIER = "./cp2cont.sh"  # the path to script that copies all unittests binaries and libs into the container
DOCKER_DIR = "/opt"  # the container internal path where to put and run all unittests
UT_WRAPPER = "runut.sh"  # script used to run _ut both in docker and vagrant
DOCKER_UT_WRAPPER = DOCKER_DIR + "/" + UT_WRAPPER  # a shell script to execute a unittest in the container

UT_USE_VAGRANT = True

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
    'Nat2': '192.168.110.2',  # the seconary iface of the Nat vm
    'Behind': '192.168.110.3',
}

UT_BOX_VAR = "Ut"  # used in BOXES_NAMES_FILE
UT_BOX_NAME = "utbox"
UT_BOX_IP = '192.168.101.2'
UT_VAG_DIR = "./vagrant_ut"
UT_VAG_UT_SUBDIR = "ut"
#UT_VAG_TEMPDIR = UT_TEMP_DIR
UT_BOX_TTL = 60 * 60 * 24 * 7  # How long the ut vm could run until it's restarted

CHECK_BOX_UP = frozenset(['Box1', 'Box2', 'Behind'])

def _boxBehindPostStartArgs(conf):
    return [conf.BOX_IP['Nat2']]  # it should be a list, not a tupple

BOX_POST_START = {
    'Behind': ('post-create-behind-nat.sh', _boxBehindPostStartArgs)
}


BOXES_NAMES_FILE = 'boxes.rb'  # os.path.join(VAG_DIR, 'boxes.rb')

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
#   'legacy' - to skip legacy functests
}

# Skip these test for all branches
SKIP_ALL = set() # {'msarch'}

SUDO_REQUIRED = set(('mediaserver_core_ut',))  # set of unittests that require sudo to call
# NOTE: SUDO_REQUIRED not used when the docker used since in a container all test executed by root

NOSHUFFLE = (  # list of tupples (branch, ut), any part can be '*' which means 'any'
    ('dev_2.5', 'mediaserver_core_ut'),
    ('prod_2.5', 'mediaserver_core_ut'),
)

# Build only this branches, don't perform any testing
BUILD_ONLY_BRANCHES = set()

SUBPROC_ARGS = dict(universal_newlines=True, shell=False)

FT_AFTER_FAILED_UT = True  # Run func.tests even if unittests failed
#------------------------------------------------------------------

try:
    import testconf_local # we need itself to access it's file name
    from testconf_local import *
except ImportError:
    pass

# Some SELF-checks
if UT_USE_DOCKER and UT_USE_VAGRANT:
    raise AssertionError("BAD CONFIGURATION: both UT_USE_DOCKER and UT_USE_VAGRANT are True!")
