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


TIMEOUT = 10 * 1000  # milliseconds

TESTS = ('common_ut', 'mediaserver_core_ut')

MAIL_FROM = "autotest-script"
MAIL_TO = 'dlavrentyuk@networkoptix.com'

