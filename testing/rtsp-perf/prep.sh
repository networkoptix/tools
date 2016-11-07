#!/bin/bash
DIR=$1
mkdir $DIR
cd $DIR
for f in timetest.py testboxes.py stortest.py generator.py functest_util.py functest.py; do
    ln -s ../$f .
done
ln -s ../mftest.cfg functest.cfg

