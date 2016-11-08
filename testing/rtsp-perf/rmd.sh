#!/bin/bash
NUM=$1
echo -n "Removing: "
for ((i=$NUM; i>0; i--)); do
    if [ -x $i ]; then
        echo -n "$i "
        rm -r $i
    fi
done
echo Done

