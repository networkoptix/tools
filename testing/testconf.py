__author__ = 'Danil Lavrentyuk'
"""
The main configuration file for (auto-)test scripts.
"""
import os, os.path

DEBUG = True

TEMP = '' # temporary files directory, leave it '' for the process' current directory

PROJECT_ROOT = "~/develop/netoptix_vms"

TARGET_PATH = '' # the default common base for BIN_PATH and LIB_PATH; live it '' to make fix_path() assign it
BIN_PATH = ''    # the path to the unit tests' binaries; live it '' to fix_path() assign it
LIB_PATH = ''    # the path to the unit tests' dynamic libraries; live it '' to fix_path() assign it

UT_SUBDIR = "unit_tests" # ut sources subdirectory, relative to PROJECT_ROOT


def fix_paths():
    global TEMP, PROJECT_ROOT, TARGET_PATH, BIN_PATH, LIB_PATH
    if TEMP == '':
        TEMP = os.getcwd()

    if PROJECT_ROOT.startswith('~'):
        PROJECT_ROOT = os.path.expanduser(PROJECT_ROOT)

    PROJECT_ROOT = os.path.abspath(PROJECT_ROOT)
    SUBPROC_ARGS['cwd'] = PROJECT_ROOT

    if TARGET_PATH == '':
        TARGET_PATH = os.path.join(PROJECT_ROOT, "build_environment/target")
    if BIN_PATH == '':
        BIN_PATH = os.path.join(TARGET_PATH, "bin/release")
    if LIB_PATH == '':
        LIB_PATH = os.path.join(TARGET_PATH, "lib/release")


HG_CHECK_PERIOD = 5 * 60 # seconds, complete check period, including time consumed by check, builds and tests
MIN_SLEEP = 60 # seconds, minimal sleep time after one perform before another
PIPE_TIMEOUT = 10 * 1000  # milliseconds
BUILD_LOG_LINES = 250 # How may last lines are saved to report build process failure
MVN_TERMINATION_WAIT = 15 # seconds, how long to wait mvn return code
MVN_BUFFER = 50000        # maven output pipe buffer size
MVN_THREADS = 8 # Number of threads to be used by maven (mvn -T)

# Multiple branches example: BRANCHES = ('dev_2.4.0', 'dev_2.5', 'dev_2.4.0_gui')
#  do not use '.' here except it is the only branch you check
BRANCHES = ('dev_2.4.0',)
TESTS = ('common_ut', 'mediaserver_core_ut') # unit tests' binary files names

SMTP_ADDR = 'smtp.gmail.com:587'
SMTP_LOGIN = 'service@networkoptix.com'
SMTP_PASS = 'kbnUk06boqBkwU'


MAIL_FROM = '"AutoTest System" <autotest@networkoptix.com>'
MAIL_TO = 'test-results@networkoptix.com'

#TODO
ALERT_TO = 'dlavrentyuk@networkoptix.com' # to send mail about check process fails (such as hg call fails)

#############################################

HG = "/usr/bin/hg"
MVN = "/home/danil/develop/buildenv/maven/bin/mvn"
VAGRANT = "/usr/bin/vagrant"

HG_IN = [HG, "incoming", "--quiet", "--template={branch},"]
HG_REVLIST = [HG, "incoming", "--quiet", "--template={branch};{author};{node|short};{date|isodatesec};{desc|tabindent}\n"]
HG_PULL = [HG, "pull", "--quiet"]
HG_UP = [HG, "update"]
HG_PURGE = [HG, "purge", "--all"]
HG_BRANCH = [HG, "branch"]

SUBPROC_ARGS = dict(universal_newlines=True, cwd=PROJECT_ROOT, shell=False)

try:
    from testconf_local import *
    if "update_configuration" in locals():
        update_configuration() # in could be useful since during importing it's difficult to access importer's namespace
except ImportError:
    pass

fix_paths()
