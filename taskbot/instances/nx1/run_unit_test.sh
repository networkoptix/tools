#!/bin/bash

TEST=$1
TEST_VAR=../../var/$TEST

mkdir -p $TEST_VAR
export LD_LIBRARY_PATH=../lib

ulimit -c unlimited
ulimit -n 4000

./$TEST --gtest_filter=-NxCritical.All3 \
        --gtest_shuffle \
        --tmp=$TEST_VAR \
        --log-file=../../var/$TEST.log \
        --log-level=DEBUG2
