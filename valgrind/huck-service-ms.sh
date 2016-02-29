#!/bin/bash
set -e -x

SCRIPT_PATH=$(dirname "${BASH_SOURCE[0]}")
TOOL=${1:-mem}

# Install files
MS_PATH=$(find /opt -type d -name mediaserver)
cp $SCRIPT_PATH/memcheck-ms.supp $MS_PATH/bin
cp $SCRIPT_PATH/run-ms.sh $MS_PATH/bin/mediaserver-valgrind

# Huck service
INIT_SCRIPT=$(find /etc/init -name '*mediaserver.conf')
sed -i "s/timeout 120/timeout 1200/" $INIT_SCRIPT
sed -i "s/mediaserver-bin -- -e/mediaserver-valgrind -- $TOOL/" $INIT_SCRIPT
