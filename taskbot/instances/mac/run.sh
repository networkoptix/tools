#!/bin/bash

realpath() {
    [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}

CONFIG=$1

if [ "x$CONFIG" = "x" ]
then
    echo "Config file isn't defined" > /dev/stderr && exit 1
fi

TASKBOT_CONFIG=$(realpath $CONFIG)

export TASKBOT_PLATFORM=$(uname -sm)

BIN="$HOME"/taskbot/devtools/taskbot/core/
TASKBOT="$BIN"/taskbot.py
ENVSH="$BIN"/envsh.py
PRNENV="$BIN"/prnenv.py

# Set taskbot environment
eval $($PRNENV $TASKBOT_CONFIG)

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
        $TASKBOT_CONFIG \
        "$TASKBOT_COMMONS"/scripts/update_repo.taskbot 
    then
      echo "Polling changes error" > /dev/stderr
    else
      $TASKBOT \
        --description "NX VMS build & tests ($TASKBOT_PLATFORM $TASKBOT_BRANCHNAME)" \
        $TASKBOT_CONFIG \
        run.taskbot
    fi
 
    sleep 60
done
