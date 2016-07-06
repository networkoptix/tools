#!/bin/bash
TMP=/tmp/test
mkdir -p $TMP
BASE=`dirname "$0"`
cd "$BASE"
ut="$1"
shift
if [ -n "$1" -a "$1" == "notmp" ]; then
    tmparg=
    shift
else
    tmparg="--tmp=$TMP"
    echo Temp arg: $tmparg
fi

echo Args: "$@"
LD_LIBRARY_PATH="$BASE" ./$ut "$tmparg" "$@"
RC=$?
if [ -n "$tmparg" ]; then
    tmpfiles=`ls $TMP`
    if [ -n "$tmpfiles" ]; then
        rm -r "$TMP"/*
    fi
fi
exit $RC
