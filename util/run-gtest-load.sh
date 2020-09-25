#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]; then
cat <<END
Runs GTests in threads until failed
Usage: $0 test_path gtest_filter
Options:
    N - each test instance count
END
exit 0; fi

set -e

TEST_PATH="$1"
[ "$2" ] && TEST_FILTER="--gtest_filter=$2"
TEST_NUMBER=${N:-1}

# Without this tests will not run on windows!
QT_PATH=$(dirname $(find $RDEP_PACKAGES_DIR -name Qt5Core.dll))
if [ $QT_PATH ]; then
    echo "QT path $QT_PATH"
    export PATH="$PATH:$QT_PATH"
else
    echo "QT path is not found!"
    exit 1
fi

TEST_LIST=$($TEST_PATH $TEST_FILTER --gtest_list_tests 2>/dev/null \
    | awk '{ if ($1 ~ /\.$/) { c=$1 } else { print c $1 } }' \
    | xargs echo )

function runTest() {
    while :; do
        $TEST_PATH --gtest_filter="$1" --log-level=v >"$2" 2>1
    done
}

for TEST_NAME in $TEST_LIST; do
    for INSTANCE in $(seq 1 $TEST_NUMBER); do
        OUTPUT=/tmp/$TEST_NAME.$INSTANCE.log
        runTest $TEST_NAME $OUTPUT &
        echo pid $!, log: $OUTPUT
    done
done

read -p "Press ENTER to kill all processes..."

for job in $(jobs -p); do kill -9 $job; done
for job in $(jobs -p); do wait $job; done
echo Done
