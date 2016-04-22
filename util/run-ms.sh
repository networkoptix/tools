#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs Mediaserver with comfiguration over run.sh
Usage: [OPTION=VALUE ...] run-ms.sh [<hex-id>] [ms-extra-args]
Options:
    DIR config directory to use, default $HOME/develop/mediaserver<hex-id>
END
exit 0
fi

set -e -x

ID=${1:-0}
if [ $1 ]; then shift; fi

DIR=${DIR:-$HOME/develop/mediaserver$ID}
RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh

$RUN mediaserver -e $@ \
   --conf-file=$DIR/mediaserver.conf \
   --runtime-conf-file=$DIR/run.conf \
   --log-level=DEBUG2 \
   --http-log-level=DEBUG2 \
   --ec2-tran-log-level=DEBUG2 \
   --dev-mode-key=razrazraz \
   --disable-crash-handler

