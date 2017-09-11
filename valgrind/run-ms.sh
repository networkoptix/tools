#!/bin/bash
set -e

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")
MS_PATH=$(find /opt -type d -name mediaserver)

TOOL=${1:-help}
LOG_FILE=valgrind-ms.${TOOL}.$(date +%s)
ARGS=$($SCRIPT_PATH/args.sh $TOOL $LOG_FILE)

export LD_LIBRARY_PATH=$MS_PATH/lib
if [[ "$(uname -p)" == x86* ]]; then
    MS_BIN=$MS_PATH/bin/mediaserver-bin
else
    MS_BIN=$MS_PATH/bin/mediaserver
fi

echo Output redirect: $LOG_FILE.out
set -x
valgrind $ARGS $MS_BIN -e >$LOG_FILE.out 2>&1

