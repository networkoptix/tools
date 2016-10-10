# -*- python -*-
# $Id$
# Artem V. Nikitin
# Windows config

import os

TASKBOT_ROOT = os.path.join(os.environ['HOME'], 'taskbot')
TASKBOT_VAR = os.path.join(
  TASKBOT_ROOT,
  os.environ['TASKBOT_BRANCHNAME'])
TASKBOT_DEVTOOLS_ROOT = os.path.join(TASKBOT_ROOT, 'devtools')

config = {
  'sh': '/bin/bash',
  'run_timeout': 5 * 60 * 60,
  'select_timeout': 60 * 60,
  'gzip_threshold': 128,
  'gzip_ratio': 0.9,
  'max_output_size': 3 * 1024 * 1024,
  'environment' : {
    'TASKBOT_PUBLIC_HTML_HOST': 'demo.networkoptix.com:3580',
    'TASKBOT_VAR': TASKBOT_VAR,
    'TASKBOT_BIN': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/core'),                            
    'TASKBOT_SHARE': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/windows'),
    'TASKBOT_COMMONS': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/commons'),
    'TASKBOT_REPO': TASKBOT_DEVTOOLS_ROOT,
    'TASKBOT_DEVELOP_PATH': '/cygdrive/c/develop/',
    'TASKBOT_NX_VMS_REPO': 'ssh://hg@hdw.mx/nx_vms',
    'TASKBOT_DEVTOOLS_REPO': 'ssh://hg@hdw.mx/devtools',
    }
  }

