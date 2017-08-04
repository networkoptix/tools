#!/bin/bash -xe

HOST="$1"

BUILD_COUNT_LIMIT=200
BUILDS_DIR="/vol/ftp/beta-builds/daily"
FILTER="*-server-*-linux64*.deb"
FIND_CMD="find $BUILDS_DIR -name \"$FILTER\" -print0 | xargs -0 ls -lt 2>/dev/null | head -n $BUILD_COUNT_LIMIT"

if [ "$HOST" = "" ]; then
	eval "$FIND_CMD"
else
	ssh "$HOST" "bash -c \"$FIND_CMD\""
fi
