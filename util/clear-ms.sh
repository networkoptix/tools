#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Clean up mediaservers database and setup default config
Usage: [OPTION=VALUE ...] $0 [HEX_SERVER_ID]
Options:
    DIR     config directory to wipe, default $HOME/develop/mediaserver<hex-id>.
    EMI     set to 1 to enableMultipleInstances=1, port will be also fixed.
    PART    clean up partialy, values: l(logs), d(data), e(ecs db), m(mserver db).
    SYS     system name, default muskov (the creator).
    WIPE    set to 1 to do not preserve config and static database.
END
exit 0
fi

set -x -e

ID=${1:-0}
DIR=${DIR:-$HOME/develop/mediaserver$ID}
SYS=${SYS:-muskov}
CONFIG=mediaserver.conf

if [[ "$PART" ]]; then
    [[ "$PART" =~ *l* ]] && rm $DIR/log/*
    [[ "$PART" =~ *d* ]] && rm -r $DIR/data
    [[ "$PART" =~ *e* ]] && rm $DIR/ecs.sqlite*
    [[ "$PART" =~ *m* ]] && rm $DIR/mserver.sqlite*
    exit 0
fi

mkdir -p $DIR
if [ ! "$WIPE" ]; then
    PRESERVE_DIR=/tmp/ms_preserve_$(date +%s)
    mkdir -p $PRESERVE_DIR
    mv $DIR/mediaserver.conf $DIR/ecs_static.* $PRESERVE_DIR
fi

rm -rf $DIR/*
if [ "$PRESERVE_DIR" ]; then
    mv $PRESERVE_DIR/* $DIR
    rmdir $PRESERVE_DIR
fi

[ -f $DIR/mediaserver.conf ] && exit 0

cat > $DIR/mediaserver.conf <<EOF
[General]
appserverPassword=
authKey=@ByteArray(SK_1267cfbb4010058a2c8e5d2abaf917ed)
dataDir=$DIR
guidIsHWID=0
logLevel=DEBUG2
logFile=$DIR/log//log_file
lowPriorityPassword=
publicIPEnabled=1
removeDbOnStartup=0
secureAppserverConnection=1
separateGuidForRemoteEC=1
serverGuid={0000000$ID-8aeb-7d56-2bc7-67afae00335c}
systemName=$SYS

EOF

if [[ $EMI ]]; then
cat >> $DIR/mediaserver.conf <<EOF
port=$((7001+ID))
enableMultipleInstances=1

EOF
fi
