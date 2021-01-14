#!/bin/bash
set -e

TOOL=${1:-help}
CUSTOMIZATION=${2:-networkoptix}
WHAT_TO_TEST=${3:-mediaserver} #client or mediaserver
DIRECTORY=${4:-/opt/$CUSTOMIZATION}

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")

if [ $1 == -h ]; then cat <<END
Usage:
    $0 tool [customization] [target] [derectory]
    $0 help -- show supported tools
Defaults:
    customization -- $CUSTOMIZATION
    target -- $WHAT_TO_TEST
    directory -- $DIRECTORY
END
    $SCRIPT_PATH/args.sh help 2>&1 | sed -n '1!p'
    exit 0;
fi


if [[ "$WHAT_TO_TEST" == "client" ]]; then
    LOG_FILE=valgrind-cl.${TOOL}.$(date +%s)
    BIN_VALGRIND=$(find $DIRECTORY -name client -type f | tail -1)
elif [[ "$WHAT_TO_TEST" == "mediaserver" ]]; then
    LOG_FILE=valgrind-ms.${TOOL}.$(date +%s)
    MS_PATH=$(find $DIRECTORY -type d -name mediaserver | grep /$CUSTOMIZATION | tail -1)
    echo Mediaserver path: $MS_PATH
    export LD_LIBRARY_PATH=$MS_PATH/lib
    if [[ "$(uname -m)" == x86* || "$(uname -m)" == armv7* ]]; then
        BIN_ORIGINAL=$MS_PATH/bin/mediaserver-bin
        # Get rid of capabilities.
        BIN_VALGRIND=$MS_PATH/bin/mediaserver-valgrind
        cat $BIN_ORIGINAL > $BIN_VALGRIND
        chmod 755 $BIN_VALGRIND
    else
        BIN_VALGRIND=$MS_PATH/bin/mediaserver
    fi
fi

ARGS=$($SCRIPT_PATH/args.sh $TOOL $LOG_FILE)

echo Output redirect: $LOG_FILE.out
set -x
valgrind $ARGS "$BIN_VALGRIND" -e >$LOG_FILE.out 2>&1
