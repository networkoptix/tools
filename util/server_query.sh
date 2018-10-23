#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs VMS binaries in console
Usage: [OPTION=VALUE ...] $0 [QUERY]
Options:
    H - Server host, default: localhost:7001
    U - Credentials, default: admin:qweasd123
    F - File to store results, default: /tmp/server_query.json
    B - Browser, default: empty (print to stdout)
Queries:
    Default: api/moduleInformation
    Aliases:
      c [id] - ec2/getCamerasEx[?id=...]
END
exit 0
fi

set -e -x

HOST=${H:-"localhost:7001"}
USER=${U:-"admin:qweasd123"}
FILE=${F:-"/tmp/server_query.json"}
BROWSER=$B

QUERY=${1:-"api/moduleInformation"}
case "$QUERY" in
    "c")
        QUERY="ec2/getCamerasEx"
        [ "$2" ] && QUERY+="?id=$2"
        ;;
esac

RAW=$FILE.raw
curl -u $USER -k https://$HOST/$QUERY > $RAW

if cat $RAW | python -m json.tool > $FILE; then
    if [ $BROWSER ]; then
        $BROWSER $FILE >/dev/null 2>&1 &
    else
        cat $FILE
    fi
else
    cat $RAW
fi

