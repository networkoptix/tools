__author__ = 'Danil Lavrentyuk'
"""
The main configuration file for (auto-)test scripts.
"""
import os, os.path

PROJECT_ROOT = "~/develop/netoptix_vms"
PROJECT_ROOT = "~/develop/nvms-tmp"
TEMP = '' # temporary files directory, leave it '' for the process' current directory

######################################################################
if TEMP == '':
    TEMP = os.getcwd()

if PROJECT_ROOT.startswith('~'):
    PROJECT_ROOT = os.path.expanduser(PROJECT_ROOT)

PROJECT_ROOT = os.path.abspath(PROJECT_ROOT)

TARGET_PATH = os.path.join(PROJECT_ROOT, "build_environment/target")
BIN_PATH = os.path.join(TARGET_PATH, "bin/release")
LIB_PATH = os.path.join(TARGET_PATH, "lib/release")
######################################################################


HG_CHECK_PERIOD = 5 * 60 # seconds, complete check period, including time consumed by check, builds and tests
MIN_SLEEP = 60 # seconds, minimal sleep time after one perform before another
PIPE_TIMEOUT = 10 * 1000  # milliseconds
BUILD_LOG_LINES = 250 # How may last lines are saved to report build process failure
MVN_TERMINATION_WAIT = 15 # seconds, how long to wait mvn return code

MVN_THREADS = 8 # Number of threads to be used by maven (mvn -T)

BRANCHES = ('dev_2.4.0', 'dev_2.5', 'dev_2.4.0_gui')
#BRANCHES = ('dev_2.4.0',)
TESTS = ('common_ut', 'mediaserver_core_ut')
UT_SUBDIR = "unit_tests"

SMTP_ADDR = '127.0.0.1'
SMTP_LOGIN = ''
SMTP_PASS = ''
SMTP_ADDR = 'smtp.gmail.com:587'
SMTP_LOGIN = 'dlavrentyuk@networkoptix.com'
SMTP_PASS = ''


MAIL_FROM = 'dlavrentyuk@networkoptix.com'
MAIL_TO = 'test-results@networkoptix.com'
#MAIL_TO = 'dlavrentyuk@networkoptix.com'

#TODO
ALERT_TO = 'dlavrentyuk@networkoptix.com' # to send mail about check process fails (such as hg call fails)

#############################################

HG = "/usr/bin/hg"
MVN = "/home/danil/develop/buildenv/maven/bin/mvn"

HG_IN = [HG, "incoming", "--quiet", "--template={branch},"]
HG_REVLIST = [HG, "incoming", "--quiet", "--template={branch};{author};{node|short};{date|isodatesec};{desc|tabindent}\n"]
HG_PULL = [HG, "pull", "--quiet"]
HG_UP = [HG, "update"]
HG_PURGE = [HG, "purge", "--all"]
HG_BRANCH = [HG, "branch"]

SUBPROC_ARGS = dict(universal_newlines=True, cwd=PROJECT_ROOT, shell=False)
