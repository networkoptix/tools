# -*- python -*-

config = {
  'sh': '/bin/bash',
  'run_timeout': 2 * 60 * 60,
  'select_timeout': 20 * 60,
  'gzip_threshold': 128,
  'gzip_ratio': 0.9,
  'max_output_size': 3 * 1024 * 1024,
  'environment' : {
    'TASKBOT_COMMONS': '/home/anikitin/prj/src/devtools/testing/taskbot',
    'TASKBOT_REPO': 'ssh://hg@hdw.mx/netoptix_vms' }
  }
