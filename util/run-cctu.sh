#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Runs Cloud Connectivity Test Utility
Usage: [OPTION=VALUE ...] run-cctu.sh [flags] [extra args ...]
Flags: l --listen, c --connect, e --echo, s --ssl
END
exit 0
fi

set -e -x
FLAGS=$1
if [ $1 ]; then shift; fi

MEDIATOR=${M:-10.0.2.41:3345}
if [ "$NM" ]; then MEDIATOR=""; fi

SYSTEM=${SY:-1ace6de3-71f1-497e-a063-743f94001e7f}
KEY=${KEY:-edf1f4eb-044f-4ff4-9d74-7eb906879fcf}
SERVER=${NM:-xxx}
LOG_LEVEL=${LL:-DEBUG}

if [[ "$FLAGS" == *l* ]]; then
    ARGS="--listen --cloud-credentials=${SYSTEM}:${KEY} --server-id=$SERVER"

    if [ $SC -gt 0 ]; then ARGS+=" --server-count=$SC"; fi
else
    ARGS="--connect --target=${N:-$SYSTEM}"

    if [ $BR ]; then ARGS+=" --bytes-to-receive=$BR"; fi
    if [ $BS ]; then ARGS+=" --bytes-to-send=$BS"; fi
    if [ $TC -gt 0 ]; then ARGS+=" --total-connections=$TC"; fi
    if [ $CC -gt 0 ]; then ARGS+=" --max-concurrent-connections=$CC"; fi
fi

if [[ "$FLAGS" == *e* ]]; then ARGS+=" --ping"; fi
if [[ "$FLAGS" == *s* ]]; then ARGS+=" --ssl"; fi
if [ "$MEDIATOR" ]; then ARGS+=" --enforce-mediator=$MEDIATOR"; fi
if [ "$LOG_LEVEL" ]; then ARGS+=" --log-level=$LOG_LEVEL"; fi

RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh
$RUN cloud_connect_test_util $ARGS $@

