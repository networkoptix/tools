#!/bin/bash

export TASKBOT_BRANCHNAME="dev_3.0.0"
export TASKBOT_PLATFORM=`uname -ol`
CONFIG="$HOME"/taskbot/"$TASKBOT_BRANCHNAME"/devtools/taskbot/instances/media_server/ubuntu_config.py
BIN="$HOME"/taskbot/"$TASKBOT_BRANCHNAME"/devtools/taskbot/core/
TASKBOT="$BIN"/taskbot.py
ENVSH="$BIN"/envsh.py
PRNENV="$BIN"/prnenv.py

# Set taskbot environment
eval $($PRNENV $CONFIG)

echo $TAKBOT_VAR

while true; do
    if [ -e "$TASKBOT_VAR/taskbot.stop" ]; then
        echo "Found $TASKBOT_VAR/taskbot.stop, exiting"
        break
    fi

    if ! $TASKBOT \
        --description "Poll for changes ($TASKBOT_PLATFORM $TASKBOT_BRANCHNAME)" \
        --trace \
        --timeout=0 \
        $CONFIG \
        update_repo.taskbot 
    then
      echo "Polling changes error" > /dev/stderr && exit 1
    fi

    $TASKBOT \
      --description "Media-server tests run ($TASKBOT_BRANCHNAME)" \
      $CONFIG \
      run.taskbot

    sleep 60
done
