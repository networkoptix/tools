#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Run Hole Punching Mediator with comfiguration over run.sh
Usage: [OPTION=VALUE ...] run-hpm.sh [hpm-extra-args]
Options:
    DIR config directory to use, default $HOME/develop/connection_mediator
END
exit 0
fi

set -e -x

DIR=${DIR:-$HOME/develop/mediaserver$1}
RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh

$RUN connection_mediator -e --run-without-cloud \
   --configFile=$DIR/connection_mediator.conf \
   $@

