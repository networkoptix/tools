#!/bin/bash
NUM=$1
PIDFILE=mrtsp.pids
LOGDIR=logs
mkdir -p $LOGDIR
test -e $PIDFILE && rm $PIDFILE
DATE=`date +%Y-%m-%d-%H-%M`
for ((i=$NUM; i>0; i--)); do
    echo $i ...
    if [ \! -x $i ]; then
        ./prep.sh $i
    fi
    cd $i
    python -u ./functest.py --rtsp-perf --autorollback > ../$LOGDIR/RTSP-${DATE}_${i}.log &
    lastpid=$!
    echo $lastpid
    cd ..
    echo $lastpid >> $PIDFILE
    sleep 2
done
