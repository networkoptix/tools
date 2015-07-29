__author__ = 'Danil Lavrentyuk'
"""
The main configuration file for (auto-)test scripts.
"""
import os.path

PROJECT_ROOT = "~/develop/netoptix_vms"

######################################################################
if PROJECT_ROOT.startswith('~'):
    PROJECT_ROOT = os.path.expanduser(PROJECT_ROOT)

PROJECT_ROOT = os.path.abspath(PROJECT_ROOT)

TARGET_PATH = os.path.join(PROJECT_ROOT, "build_environment/target")
BIN_PATH = os.path.join(TARGET_PATH, "bin/release")
LIB_PATH = os.path.join(TARGET_PATH, "lib/release")
######################################################################


HG_CHECK_PERIOD = 3 * 60 # seconds, complete check period, including time consumed by check, builds and tests
MIN_SLEEP = 30 # seconds, minimal sleep time after one perform before another
PIPE_TIMEOUT = 10 * 1000  # milliseconds

BRANCHES = ('dev_2.4.0', 'dev_2.5', 'prod_2.3.2')
TESTS = ('common_ut', 'mediaserver_core_ut')

MAIL_FROM = "autotest-script"
MAIL_TO = 'dlavrentyuk@networkoptix.com'

