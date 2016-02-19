#!/bin/bash
set -e -x

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")
MS_PATH=/opt/networkoptix/mediaserver
LOG_FILE=valgrind-ms.$TOOL.out.$(date +%s)

TOOL=${1:-mem}
case $TOOL in
  *mem*)
    ARGS='-v --leak-check=yes --suppressions="$SCRIPT_DIR/memcheck-ms.supp"'
    ;;
  *dhat*)
    ARGS="--tool=exp-dhat --show-top-n=100 --sort-by=max-bytes-live"
    ;;
  *massif*)
    ARGS="--tool=massif"
  *)
    echo Unsupported tool $TOOL >&2
    ;;
esac


export LD_LIBRARY_PATH=$MS_PATH/lib
valgrind $ARGS $MS_PATH/bin/mediaserver-bin -e >$LOG_FILE 2>&1

