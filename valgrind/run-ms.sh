#!/bin/bash
set -e

TOOL=${1:-help}
CUSTOMIZATION=$2
WHAT_TO_TEST=${3:-mediaserver} #client or mediaserver

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")

if [[ "$WHAT_TO_TEST" == "client" ]]; then
    LOG_FILE=valgrind-cl.${TOOL}.$(date +%s)
    CL_PATH=$(find /opt -type d | grep client | grep /$CUSTOMIZATION | head -1)
    echo Client path: $CL_PATH
    export LD_LIBRARY_PATH=$CL_PATH/*/lib
    export DISPLAY=:0
    if [[ "$(uname -p)" == x86* ]]; then
        BIN_ORIGINAL=$CL_PATH/*/bin/client-bin
        BIN_VALGRIND=$BIN_ORIGINAL
    else
        BIN_ORIGINAL=$CL_PATH/*/bin/client
        BIN_VALGRIND=$BIN_ORIGINAL
    fi
elif [[ "$WHAT_TO_TEST" == "mediaserver" ]]; then
    LOG_FILE=valgrind-ms.${TOOL}.$(date +%s)
    MS_PATH=$(find /opt -type d -name mediaserver | grep /$CUSTOMIZATION | head -1)
    echo Mediaserver path: $MS_PATH
    export LD_LIBRARY_PATH=$MS_PATH/lib
    if [[ "$(uname -p)" == x86* ]]; then
        BIN_ORIGINAL=$MS_PATH/bin/mediaserver-bin
        # Get rid of capabilities.
        BIN_VALGRIND=$MS_PATH/bin/mediaserver-valgrind
        cat $BIN_ORIGINAL > $BIN_VALGRIND
        chmod 755 $BIN_VALGRIND
    else
        BIN_ORIGINAL=$MS_PATH/bin/mediaserver
    fi
fi

ARGS=$($SCRIPT_PATH/args.sh $TOOL $LOG_FILE)

echo Output redirect: $LOG_FILE.out
set -x
valgrind $ARGS $BIN_VALGRIND -e >$LOG_FILE.out 2>&1

