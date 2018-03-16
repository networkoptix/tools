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

case $PWD in
    *-2.*)          BINARY=client.bin       ;;
    *-3.0*|*-3.1*)  BINARY=desktop_client   ;;
    *)              BINARY=client-bin       ;;
esac

echo logs: '".local/share/Network\ Optix/Network\ Optix\ HD\ Witness\ Client/log/log_file.log"'
$(dirname "${BASH_SOURCE[0]}")/run.sh $BINARY $ARGS $@

