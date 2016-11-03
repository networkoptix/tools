#!/bin/bash
NUM=$1
PIDFILE=mrtsp.pids
test -e $PIDFILE && rm $PIDFILE
DATE=`date +%Y-%m-%d-%H-%M`
for ((i=$NUM; i>0; i--)); do
    echo $i ...
    cd $i
    python -u ./functest.py --rtsp-perf --autorollback > ../10.1.5.121-M-${DATE}_${i}.log &
    lastpid=$!
    echo $lastpid
    cd ..
    echo $lastpid >> $PIDFILE
    sleep 1
done
