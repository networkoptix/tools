#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]; then
cat <<END
Runs Unit Tests over run.sh
Usage: run-ut.sh [tests ...]
Options:
    J - max concurent test executions, default is 12
    DIR - output directory, default is /tmp/ut/
    LL  - log level to use, default is no log at all
END
exit 0; fi

set -e
[ "$X" ] && set -x

MAX_JOBS=${J:-12}
RUN=$(dirname "${BASH_SOURCE[0]}")/run.sh
DEFAULT_DIR=/tmp/nx_vms_ut

if [ ! "$DIR" ]; then
    DIR=$DEFAULT_DIR/$(date +%s)
    rm -rf $DEFAULT_DIR
else
    rm -rf $DIR
fi

echo '-----' Prepare to run tests in: $DIR
mkdir -p $DIR

TESTS=$@
if [ ! "$TESTS" ]; then
    TESTS=$(find build_environment -name "*_ut" -type f |
        tr '/' ' ' | awk '{print $NF}')
fi
[ "$TESTS" == n ] && TESTS="nx_network_ut cloud_connectivity_ut"

function run_async() {
    set +e
    local tmpDir="$DIR/$1.$2.tmp"
    local args="--gtest_filter=$2.* --gtest_shuffle --gtest_break_on_failure --tmp=$tmpDir"
    local out="$DIR/$1.$2.out"
    [ $LL ] && args+=" --ll=$LL"
    [ $EA ] && args+=" $EA"

    mkdir -p "$tmpDir"
    echo '>>>>>' START: $@
    $RUN $1 $args > $out 2>&1
    local result=$?
    if [ $result != "0" ]; then
        echo '<<<<<' FAILURE: $@ '>' $out
        tail "$out"
    else
        rm -rf $tmpDir
    fi

    return $result
}

for name in $TESTS; do
    test_case_list=$($RUN $name --gtest_list_tests 2>/dev/null |\
        grep '\.' | grep -v DISABLED | awk '{print $1}')
    for test_case in $test_case_list; do
        while (($(jobs -rp | wc -l) >= $MAX_JOBS)); do
            sleep 0.1
        done

        test_case=$(echo $test_case | tr '.' ' ')
        run_async $name $test_case &
    done
done

for job in $(jobs -p); do
    wait $job
done
echo '=====' DONE
