#!/bin/bash

TEST=$1
TEST_VAR=../../var/$TEST

mkdir -p $TEST_VAR
BIN_PATH=$(pwd)
LIB_PATH=$BIN_PATH/../lib
export LD_LIBRARY_PATH=$LIB_PATH:/opt/networkoptix/lib:/opt/networkoptix/mediaserver/lib

ulimit -c unlimited
ulimit -n 4000

if [ "$TEST" != "mediaserver_core_ut" ]; then
  ./$TEST --gtest_filter=-NxCritical.All3 \
          --gtest_shuffle \
          --tmp=$TEST_VAR \
          --log-file=../../var/$TEST \
          --log-size=20M \
          --log-level=DEBUG2
else
  ./$TEST --gtest_filter=-NxCritical.All3 \
          --gtest_shuffle \
          --tmp=$TEST_VAR
fi
