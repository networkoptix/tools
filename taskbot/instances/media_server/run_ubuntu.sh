#!/bin/bash

CONFIG="$HOME"/prj/src/devtools/taskbot/instances/media_server/ubuntu_config.py
BIN=~/prj/src/devtools/taskbot/core/
TASKBOT="$BIN"/taskbot.py
ENVSH="$BIN"/envsh.py
PRNENV="$BIN"/prnenv.py

# Set taskbot environment
eval $($PRNENV $CONFIG)

$TASKBOT \
  --description "Poll for changes ($TASKBOT_BRANCHNAME)" \
  --trace \
  $CONFIG \
  update_repo.taskbot

$TASKBOT \
  --description "Media-server tests run ($TASKBOT_BRANCHNAME)" \
  $CONFIG \
  run.taskbot