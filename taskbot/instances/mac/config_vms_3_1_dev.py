# -*- python -*-
# $Id$
# Artem V. Nikitin
# Mac config

import os

TASKBOT_BRANCHNAME='vms_3.1_dev'
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
    'Mikhail Uskov': 'muskov@networkoptix.com',
    'Vsevolod Fedorov': 'vfedorov@networkoptix.com',
    },
  'environment' : {
    'TASKBOT_BRANCHNAME': TASKBOT_BRANCHNAME,
    'TASKBOT_PUBLIC_HTML_HOST': 'taskbot.hdw.mx',
    'TASKBOT_VAR': TASKBOT_VAR,
    'TASKBOT_BIN': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/core'),
    'TASKBOT_SHARE': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/mac'),
    'TASKBOT_COMMONS': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/commons'),
    'TASKBOT_REPO': TASKBOT_DEVTOOLS_ROOT,
    'TASKBOT_NX_VMS_REPO': 'ssh://hg@hdw.mx/nx_vms',
    'TASKBOT_DEVTOOLS_REPO': 'ssh://hg@hdw.mx/devtools',
    'TASKBOT_UNIT_TESTS': 'all',
    }
  }
