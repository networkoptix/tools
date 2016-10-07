# -*- python -*-

config = {
  'sh': '/bin/bash',
  'run_timeout': 5,
  'select_timeout': 10,
  'gzip_threshold': 128,
  'gzip_ratio': 0.9,
  'max_output_size': 3 * 1024 * 1024,
  'environment' : {
    'TASKBOT_COMMONS': '/home/anikitin/taskbot/devtools/taskbot',
    'TASKBOT_REPO':  'ssh://hg@enk.me/devtools'}
  }
