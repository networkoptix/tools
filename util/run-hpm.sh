#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs Hole Punching Mediator with comfiguration over run.sh
Usage: [OPTION=VALUE ...] run-hpm.sh [hpm-extra-args]
Options:
    DIR config directory to use, default $HOME/develop/connection_mediator
END
exit 0
fi

set -e -x

DIR=${DIR:-$HOME/develop/connection_mediator}
RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh

$RUN connection_mediator -e \
   --configFile=$DIR/connection_mediator.conf \
   $@

