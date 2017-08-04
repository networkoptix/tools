#!/bin/bash -xe

HOST="$1"
BUILD="$2"
BRANCH="$3"
CUSTOMIZATION="$4"

BUILDS_DIR="/vol/ftp/beta-builds/daily"
SELECTED_BUILD_DIR="$BUILDS_DIR/${BUILD}-${BRANCH}/${CUSTOMIZATION}/"
FILTER="*-server-*-linux64*.deb"
FIND_CMD="find $SELECTED_BUILD_DIR -name \"$FILTER\""

if [ "$HOST" = "" ]; then
	eval "$FIND_CMD"
else
	ssh "$HOST" "bash -c \"$FIND_CMD\""
fi
