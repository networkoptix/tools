# -*- python -*-
# $Id$
# Artem V. Nikitin
# Windows config

import os

TASKBOT_BRANCHNAME='vms_3.1_gui'
TASKBOT_ROOT = os.path.join(os.environ['HOME'], 'taskbot')
TASKBOT_VAR = os.path.join(
  TASKBOT_ROOT, TASKBOT_BRANCHNAME)
TASKBOT_DEVTOOLS_ROOT = os.path.join(TASKBOT_ROOT, 'devtools')

config = {
  'sh': '/bin/bash',
  'run_timeout': 2 * 60 * 60,
  'select_timeout': 20 * 60,
  'gzip_threshold': 128,
  'gzip_ratio': 0.9,
  'max_output_size': 3 * 1024 * 1024,
  'watchers': {
    'Sergey Ivanov' : 'sivanov@networkoptix.com',
    },
  'environment' : {
    'CDB_PATH': '/cygdrive/c/Program Files (x86)/Windows Kits/10/Debuggers/x64/cdb.exe',
    'TASKBOT_BRANCHNAME': TASKBOT_BRANCHNAME,
    'TASKBOT_PUBLIC_HTML_HOST': 'demo.networkoptix.com:3580',
    'TASKBOT_VAR': TASKBOT_VAR,
    'TASKBOT_BIN': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/core'),                            
    'TASKBOT_SHARE': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/windows'),
    'TASKBOT_COMMONS': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/commons'),
    'TASKBOT_REPO': TASKBOT_DEVTOOLS_ROOT,
    'TASKBOT_NX_VMS_REPO': 'ssh://hg@hdw.mx/nx_vms',
    'TASKBOT_DEVTOOLS_REPO': 'ssh://hg@hdw.mx/devtools',
    'TASKBOT_UNIT_TESTS': 'client_ut common_ut nx_fusion_ut vms_utils_ut utils_ut'
    }
  }

