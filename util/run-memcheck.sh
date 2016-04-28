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

OPTS+=" --leak-check=full --show-leak-kinds=all"
OPTS+=" --num-callers=100 --error-limit=no"
OPTS+=" --suppressions=$SCRIPT_DIR/vms-valgrind.supp"

if [ $VGS ]; then
    OPTS+=" --gen-suppressions=all"
fi

V="$OPTS" $SCRIPT_DIR/run.sh $@

