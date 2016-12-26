#!/bin/bash
set -e -x

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")
MS_PATH=$(find /opt -type d -name mediaserver)

TOOL=${1:-mem}
LOG_FILE=valgrind-ms.${TOOL}.out.$(date +%s)

case $TOOL in
  *mem*)
    ARGS="-v --leak-check=yes --suppressions=$SCRIPT_PATH/memcheck-ms.supp"
    ;;
  *dhat*)
    ARGS="--tool=exp-dhat --show-top-n=100 --sort-by=max-bytes-live"
    ;;
  *mass*)
    ARGS="--tool=massif"
    ;;
  *call*)
    ARGS="--tool=callgrind --callgrind-out-file=${LOG_FILE}.cg"
    ;;
  *)
    echo Unsupported tool $TOOL >&2
    exit 1
    ;;
esac

export LD_LIBRARY_PATH=$MS_PATH/lib
if [ $(uname -p) == x86* ]; then
    MS_BIN=$MS_PATH/bin/mediaserver-bin
else
    MS_BIN=$MS_PATH/bin/mediaserver
fi

valgrind $ARGS $MS_BIN -e >$LOG_FILE 2>&1

