#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs NX VMS binaries in valgrind memcheck over run.sh
Usage: [OPTION=VALUE ...] run-ms.sh <bin-name> [bin-args]
Options:
    OPTS extra valgrind options
    VGS generate suppressions if not empty
END
exit 0
fi

SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
DEV_TOOLS=$(readlink $SCRIPT_DIR)/..

BIN=$1
shift
ARGS="$@"

KINDS=${KINDS:-definite,possible}
UNDEF=${UNDEF:-no}

OPTS+=" --leak-check=full --show-leak-kinds=$KINDS --undef-value-errors=$UNDEF"
OPTS+=" --num-callers=100 --error-limit=no"
OPTS+=" --suppressions=$DEV_TOOLS/valgrind/memcheck-ms.supp"

[ $X ] && set -x
[ $VGS ] && OPTS+=" --gen-suppressions=all"

if [[ "$OUT" ]]; then
    OUT=/tmp/$BIN.vg.$OUT
    echo Redirect output: $OUT
    V="$OPTS" $SCRIPT_DIR/run.sh $BIN $ARGS > $OUT 2>&1
else
    V="$OPTS" $SCRIPT_DIR/run.sh $BIN $ARGS
fi

