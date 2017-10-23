#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs Mediaserver with comfiguration over run.sh
Usage: [OPTION=VALUE ...] run-ms.sh [<hex-id>] [ms-extra-args]
Options:
    DIR - config directory to use, default $HOME/develop/mediaserver<hex-id>
    LL  - log level to use (DEBUG2 is default)
    CH  - disable crash handler
END
exit 0
fi

if [ $WINDIR ]; then
    DEFAULT_DEVELOP=/c/develop
else
    DEFAULT_DEVELOP=$HOME/develop
fi

set -e -x

ID=${1:-0}
if [ $1 ]; then shift; fi

DIR=${DIR:-$DEFAULT_DEVELOP/mediaserver$ID}
ARGS="-e --conf-file=$DIR/mediaserver.conf --runtime-conf-file=$DIR/run.conf"
if [ ! $noD ]; then ARGS+=" --dev-mode-key=razrazraz"; fi

$(dirname "${BASH_SOURCE[0]}")/run.sh mediaserver $ARGS $@

