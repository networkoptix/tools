#!/bin/bash

# Packes specified executable file and its dependencies (excluding libraries from system directories) into an archive

function printHelp {
    echo "Usage: $0 /path/to/executable"
}

if [[ "$1" == "-h" || "$1" == "--help" || "$#" -ne 1 ]]; then
    printHelp
    exit 0
fi

FILENAME=$1
ARCHIVE_NAME="$(basename $FILENAME).tar.gz"
TMP_DIR=./tmp

if [ ! -f $FILENAME ]; then
    echo "$FILENAME does not exist"
    exit 1
fi

echo "Packing $FILENAME and dependencies into $ARCHIVE_NAME"

mkdir $TMP_DIR || exit 1
ldd $FILENAME | grep -v " /lib/" | grep -v "/usr/lib/" | grep -v "/lib64" | grep "=>" | sed 's/.*=> \(.*\) (.*/\1/g' | xargs -IXXX cp XXX $TMP_DIR
cp $FILENAME $TMP_DIR
tar czf $ARCHIVE_NAME $TMP_DIR/*
rm -rf $TMP_DIR
