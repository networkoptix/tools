export TASKBOT_BRANCHNAME="dev_3.0.0"

if [ ! -z "$1" ]; then
  export TASKBOT_BRANCHNAME="$1"  
fi

export TASKBOT_PLATFORM=$(uname -ms | sed -r 's/CYGWIN_/WIN\
TASKBOT_CONFIG="$HOME"/taskbot/devtools/taskbot/instances/windows/config.py
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
      echo "Polling changes error" > /dev/stderr && exit 1
    fi

    $TASKBOT \
      --description "NX VMS build & tests ($TASKBOT_PLATFORM $TASKBOT_BRANCHNAME)" \
      $TASKBOT_CONFIG \
      run.taskbot

    sleep 60
done
