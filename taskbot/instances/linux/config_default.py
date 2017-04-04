# -*- python -*-
# $Id$
# Artem V. Nikitin
# Linux config

import os

TASKBOT_BRANCHNAME='default'
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
    'Artem Nikitin': 'anikitin@networkoptix.com',
    'Roman Vasilenko': 'rvasilenko@networkoptix.com',
    'Sergey Ivanov' : 'sivanov@networkoptix.com',
    'Andrey Kolesnikov': 'akolesnikov@networkoptix.com'},
  'ft_watchers': {
    'Artem Nikitin': 'anikitin@networkoptix.com',
    'Andrey Kolesnikov': 'akolesnikov@networkoptix.com',
    'Vsevolod Fedorov': 'vfedorov@networkoptix.com',
    'Alexandra Matveeva': 'amatveeva@networkoptix.com',
    'Roman Vasilenko': 'rvasilenko@networkoptix.com'  },
  'environment' : {
    'TASKBOT_BRANCHNAME': TASKBOT_BRANCHNAME,
    'TASKBOT_PUBLIC_HTML_HOST': 'demo.networkoptix.com:3580',
    'TASKBOT_VAR': TASKBOT_VAR,
    'TASKBOT_BIN': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/core'),                            
    'TASKBOT_SHARE': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/linux'),
    'TASKBOT_COMMONS': os.path.join(TASKBOT_DEVTOOLS_ROOT, 'taskbot/instances/commons'),
    'TASKBOT_REPO': TASKBOT_DEVTOOLS_ROOT,
    'TASKBOT_NX_VMS_REPO': 'ssh://hg@hdw.mx/nx_vms',
    'TASKBOT_DEVTOOLS_REPO': 'ssh://hg@hdw.mx/devtools',
    'TASKBOT_UNIT_TESTS': 'all',
#    'TASKBOT_FUNC_TESTS': 'true',
    }
  }
