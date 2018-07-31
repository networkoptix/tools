#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs Desctop Clinet with comfiguration over run.sh
Usage: [OPTION=VALUE ...] run-dc.sh [ms-extra-args]
Options:
    LL  - log level to use (DEBUG2 is default)
END
exit 0
fi

set -e -x

LL=${LL-DEBUG2}
ARGS="--log-level=$LL --http-log-level=$LL --ec2-tran-log-level=$LL"

: ${BINARY:=$(find -name client*bin -type f)}
: ${BINARY:=$(find -name desktop_client -type f)}

if [ ! "$BINARY" ]; then
    echo Unable to find client binary. >2
    exit 1 # U
fi

echo logs: '".local/share/Network\ Optix/Network\ Optix\ HD\ Witness\ Client/log/log_file.log"'
$(dirname "${BASH_SOURCE[0]}")/run.sh $BINARY $ARGS $@

