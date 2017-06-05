#!/bin/bash

CONFIG=$1

if [ "x$CONFIG" = "x" ]
then
    echo "Config file isn't defined" > /dev/stderr && exit 1
fi

TASKBOT_CONFIG=$(realpath $CONFIG)

export TASKBOT_PLATFORM=$(uname -oi)

BIN="$HOME"/taskbot/devtools/taskbot/core/
TASKBOT="$BIN"/taskbot.py
ENVSH="$BIN"/envsh.py
PRNENV="$BIN"/prnenv.py

# Set taskbot environment
eval $($PRNENV $TASKBOT_CONFIG)

echo $TAKBOT_VAR

while true; do

    if ! $TASKBOT \
        --description "Poll for changes ($TASKBOT_PLATFORM $TASKBOT_BRANCHNAME)" \
        --trace \
        --timeout=0 \
        $TASKBOT_CONFIG \
        slow_poll.taskbot
    then
      echo "Polling changes error" > /dev/stderr
    else
      $TASKBOT \
        --description "NX VMS slow tests ($TASKBOT_PLATFORM $TASKBOT_BRANCHNAME)" \
        $TASKBOT_CONFIG \
        slow.taskbot \
        --process-lock 'functional_tests'
    fi

    sleep 60
done
