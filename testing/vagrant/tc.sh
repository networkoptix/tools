#!/bin/bash
. /vagrant/conf.sh

export LD_LIBRARY_PATH="$SERVDIR/lib"
export VMS_PLUGIN_DIR="$SERVDIR/lib/plugins"

"$SERVDIR/bin/testcamera"

"$SERVDIR/bin/testcamera" files=/vagrant/sample.mkv\;count=1 >&/tmp/testcamera.log &
TCPID=$!
sleep 1
if kill -0 $TCPID 2>/dev/null; then
    echo Testcamera PID: $TCPID
else
    exit 1
fi
