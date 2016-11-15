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

MEDIATOR=$M
SYSTEM=${SYS:-6d4a6a15-c739-43c4-8971-2c87e6630f30}
KEY=${KEY:-a75f54e2-c011-48c6-ad54-652e47db3aad}
SERVER=${NM:-srv}
LOG_LEVEL=${LL:-DEBUG}
RW_TIMEOUT=${TO:-3s}

if [[ "$FLAGS" == *l* ]]; then
    ARGS="--listen --cloud-credentials=${SYSTEM}:${KEY} --server-id=$SERVER"
    if [ $SC -gt 0 ]; then ARGS+=" --server-count=$SC"; fi
else
    ARGS="--connect --target=${N:-$SYSTEM}"
    if [ $SC -gt 0 ]; then ARGS+=" --server-id=$SERVER --server-count=$SC"; fi

    if [ $BR ]; then ARGS+=" --bytes-to-receive=$BR"; fi
    if [ $BS ]; then ARGS+=" --bytes-to-send=$BS"; fi
    if [ $TC -gt 0 ]; then ARGS+=" --total-connections=$TC"; fi
    if [ $CC -gt 0 ]; then ARGS+=" --max-concurrent-connections=$CC"; fi
fi

if [[ "$FLAGS" == *e* ]]; then ARGS+=" --ping"; fi
if [[ "$FLAGS" == *s* ]]; then ARGS+=" --ssl"; fi
if [[ "$FLAGS" == *f* ]]; then ARGS+=" --forward-address"; fi
if [ "$MEDIATOR" ]; then ARGS+=" --enforce-mediator=$MEDIATOR"; fi
if [ "$LOG_LEVEL" ]; then ARGS+=" --log-level=$LOG_LEVEL"; fi
if [ "$RW_TIMEOUT" ]; then ARGS+=" --rw-timeout=$RW_TIMEOUT"; fi

RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh
$RUN cloud_connect_test_util $ARGS $@

