#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs tail with grep on mediaserver log file with grep.
Usage: [OPTION=VALUE ...] $0 [paterns ...]
Options:
    DIR - config directory to use, default $HOME/develop/mediaserveri\$SRC
    WIN - service name on windows
    SRC - integer is for mediaserver id, "c" is for client
END
exit 0
fi

set -e
[ $X ] && set -x

if [ ! "$DIR" ]; then
    if [ "$WIN" ]; then
        DIR="/c/Users/mux/AppData/Local/*/*$WIN*"
    else
        SRC=${SRC:-*}
        if [ $SRC == c ]; then
            DIR="$HOME/.local/share/Network*/*"
        else
            DIR="$HOME/develop/mediaserver$SRC"
        fi
    fi
fi

PATTERN=START
GREP_OPTIONS=""
while [ ! -z "$1" ]; do
    if [[ "x$1" == x-* ]]; then
        GREP_OPTIONS+="$1"
    else
        PATTERN+="\|$1"
    fi
    shift
done

set -x
tail -F $DIR/log/log_file.log | grep $GREP_OPTIONS "$PATTERN"
