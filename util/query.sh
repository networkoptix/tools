#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs VMS binaries in console
Usage: [OPTION=VALUE ...] $0 QUERY [OPTIONS]
Options:
    H - Server host, default: localhost:7001
    U - Credentials, default: admin:qweasd123
    F - File to store results, default: /tmp/server_query.json
    B - Browser, default: empty (print to stdout)
Query aliases:
    m      - api/moduleInformation (default)
    c [id] - ec2/getCameras[Ex?id=...]
    s [id] - ec2/getMediaServers[Ex?id=...]
END
exit 0
fi

set -e -x

HOST=${H:-"localhost:7001"}
USER=${U:-"admin:QWEasd123"}
FILE=${F:-"/tmp/server_query.json"}
BROWSER=$B

QUERY=${1:-"api/moduleInformation"}; shift
case "$QUERY" in
    "m")
        QUERY="api/moduleInformation"
        ;;
    "c")
        QUERY="ec2/getCameras$E"
        if [ "$1" ]; then QUERY+="?id=$1"; shift; fi
        ;;
    "s")
        QUERY="ec2/getMediaServers$E"
        if [ "$1" ]; then QUERY+="?id=$1"; shift; fi
        ;;
esac

RAW=$FILE.raw
curl -u $USER -k https://$HOST/$QUERY "$@" > $RAW

if cat $RAW | python -m json.tool > $FILE; then
    if [ $BROWSER ]; then
        $BROWSER $FILE >/dev/null 2>&1 &
    else
        cat $FILE
    fi
else
    cat $RAW
fi

