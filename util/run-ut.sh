#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]; then
cat <<END
Runs Unit Tests over run.sh
Usage: run-ut.sh [tests ...]
Options:
    DIR - output directory, default is /tmp/ut/
    LL  - log level to use (no log is default)
END
exit 0; fi

set -e
[ "$X" ] && set -x

DIR=${DIR:-/tmp/ut}
mkdir -p $DIR

FILTER_nx_network_ut="*Socket*"
FILTER_cloud_connectivity_ut="*Socket*"

TESTS=$@
if [ ! "$TESTS" ]; then
    TESTS=$(find build_environment -name "*_ut" -type f |
        tr '/' ' ' | awk '{print $NF}')
fi
[ "$TESTS" == n ] && TESTS="nx_network_ut cloud_connectivity_ut"

function run_async() {
    set +e
    EXTRA="--gtest_shuffle --gtest_break_on_failure"
    OUT=$DIR/$1.$(date +%N).out
    [ $LL ] && EXTRA+=" --ll=$LL"

    echo '>>>>>' START: $@ \> $OUT
    $(dirname "${BASH_SOURCE[0]}")/run.sh $@ $EXTRA >$OUT 2>&1
    RESULT=$?
    if [ $RESULT == "0" ]; then
        echo '<<<<<' SUCCESS: $@
    else
        echo '<<<<<' FAILURE: $@ \> $OUT
        tail $OUT
    fi

    return $RESULT
}

for TEST in $TESTS; do
    eval FILTER=\$FILTER_$TEST
    if [ "$FILTER" ]; then
        run_async $TEST "--gtest_filter=$FILTER" &
        run_async $TEST "--gtest_filter=-$FILTER" &
    else
        run_async $TEST &
    fi
done

FAIL=0
for JOB in $(jobs -p); do
    wait $JOB || ((FAIL+=1))
done
if [ $FAIL == 0 ]; then
    echo '=====' COMPLETE SUCCESS
else
    echo '=====' $FAIL TESTS FAILED
fi

