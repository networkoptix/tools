#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs tail with grep on mediaserver log file with grep.
Usage: [OPTION=VALUE ...] $0 [paterns ...]
Options:
    D   = config directory to use, default $HOME/develop/mediaserveri\$SRC
    W   = service name on windows
    S   = integer is for mediaserver id, "c" is for client
END
exit 0
fi

set -e
[ $X ] && set -x

if [ "$D" ]; then
    DIRECTORY="$D"
else
    if [ "$W" ]; then
        DIRECTORY="/c/Users/mux/AppData/Local/*/*$W*"
    else
        SOURCE=${S:-*}
        if [ "$SOURCE" == c ]; then
            DIRECTIRY="$HOME/.local/share/Network*/*"
        else
            DIRECTORY="$HOME/develop/mediaserver$SOURCE"
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
tail -F $DIRECTORY/log/log_file.log | grep $GREP_OPTIONS "$PATTERN"
