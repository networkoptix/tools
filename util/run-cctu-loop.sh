#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Runs Cloud Connectivity Test Utility in infinity loop
Usage: [OPTION=VALUE ...] run-cctu.sh [flags] [extra args ...]
Flags: l --listen, c --connect, e --echo, s --ssl
END
exit 0
fi

if [[ $X ]]; then
    set -x
else
    export NOX=1
fi

RUN=$(dirname "${BASH_SOURCE[0]}")/run-cctu.sh
while :; do
    $RUN $@
    [[ $? == 130 ]] && exit 130
done
