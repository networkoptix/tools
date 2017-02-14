#!/bin/bash

TEST=$1
TEST_VAR=../../var/$TEST

mkdir -p $TEST_VAR
export LD_LIBRARY_PATH=../lib

ulimit -c unlimited

./$TEST --gtest_filter=-NxCritical.All3 --gtest_shuffle --tmp=$TEST_VAR
