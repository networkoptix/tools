# -*- python -*-

import os

TASKBOT_ROOT = os.path.join(os.environ['HOME'], 'taskbot')
BRANCH_NAME = 'Ubuntu'
TASKBOT_VAR = os.path.join(TASKBOT_ROOT, BRANCH_NAME)
#TASKBOT_DEVTOOLS_ROOT = os.path.join(TASKBOT_ROOT, 'repo', 'devtools')
TASKBOT_DEVTOOLS_ROOT = os.path.join(os.environ['HOME'], 'prj/src/devtools')

config = {
  'sh': '/bin/bash',
  'run_timeout': 2 * 60 * 60,
  'select_timeout': 20 * 60,
  'gzip_threshold': 128,
  'gzip_ratio': 0.9,
  'max_output_size': 3 * 1024 * 1024,
  'environment' : {
#    'TASKBOT_BUILD': '/home/anikitin/prj/src/devtools/taskbot',
    'TASKBOT_BRANCHNAME': BRANCH_NAME,
    'TASKBOT_VAR': TASKBOT_VAR,
    'TASKBOT_BIN': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/core'),                            
    'TASKBOT_SHARE': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/media_server'),
    'TASKBOT_REPO': TASKBOT_DEVTOOLS_ROOT,
    'TASKBOT_NX_VMS_REPO': 'ssh://hg@hdw.mx/nx_vms',
    'TASKBOT_NX_VMS_BRANCH': 'dev_3.0.0',
    'TASKBOT_DEVTOOLS_REPO': 'ssh://hg@enk.me/devtools',
    }
  }
