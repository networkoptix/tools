#!/bin/bash
# Being called from autotest/tools.py, copy unittests and libs into container.
if [ -z "$1" -o -z "$2" -o -z "$3" -o -z "$4" -o -z "$5" ]; then
    echo "Too few parameters!" 1>&2
    echo Usage:
    echo "$0" CONTAINER DEST_DIR BIN_PATH LIB_PATH QT_LIB_PATH
    exit 1
fi

CONTAINER="$1"
DEST_DIR="$2"
BIN_PATH="$3"
LIB_PATH="$4"
QT_LIB_PATH="$5"

for ut in "$BIN_PATH"/*_ut; do
    docker cp "$ut" $CONTAINER:$DEST_DIR
done

docker cp runut.sh $CONTAINER:$DEST_DIR

(cd "$LIB_PATH";tar -c *.so *.so.*) | docker cp - $CONTAINER:$DEST_DIR

(cd "$QT_LIB_PATH";tar -c *.so *.so.*) | docker cp - $CONTAINER:$DEST_DIR


