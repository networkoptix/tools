#!/bin/bash

export TASKBOT_BRANCHNAME="dev_3.0.0"

if [ ! -z "$1" ]; then
  export TASKBOT_BRANCHNAME="$1"  
fi

export TASKBOT_PLATFORM=`uname -oi`
TASKBOT_CONFIG="$HOME"/taskbot/devtools/taskbot/instances/linux/config_dev_3_0_0.py
BIN="$HOME"/taskbot/devtools/taskbot/core/
TASKBOT="$BIN"/taskbot.py
ENVSH="$BIN"/envsh.py
PRNENV="$BIN"/prnenv.py

# Set taskbot environment
eval $($PRNENV $TASKBOT_CONFIG)

TASKBOT_DEBUG_MODE=1 TASKBOT_REPO="$TASKBOT_REPO" "$TASKBOT_COMMONS"/reports/build_report.py "$TASKBOT_CONFIG"
