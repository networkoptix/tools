#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Clean up mediaservers database and setup default config
Usage: [OPTION=VALUE ...] $0 [HEX_SERVER_ID]
Options:
    DIR     config directory to wipe, default $HOME/develop/mediaserver<HEX_SERVER_ID>.
    EMI     set to 1 to enableMultipleInstances=1, port will be also fixed.
    PART    clean up partialy, values: l(logs), d(data), e(ecs db), m(mserver db).
    SYS     system name, default muskov (the creator).
    PERSONAL_ID 
            4 char long hex value unique for developer, default '8aeb'.
    WIPE    set to 1 to do not preserve config and static database.
END
exit 0
fi

if [ $WINDIR ]; then
    DEFAULT_DEVELOP=/c/develop
else
    DEFAULT_DEVELOP=$HOME/develop
fi

set -x -e

ID=${1:-0}
PERSONAL_ID=${PERSONAL_ID:-8aeb}
DIR=${DIR:-$DEFAULT_DEVELOP/mediaserver$ID}
SYS=${SYS:-muskov}
CONFIG=mediaserver.conf

if [[ ! $PERSONAL_ID =~ ^[a-f0-9]{4}$ ]]
then
    echo "Error: PERSONAL_ID must be 4 chars long hex value!"
    exit 1
fi

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
    mv $DIR/mediaserver.conf $DIR/ecs_static.* $PRESERVE_DIR || true
fi

rm -rf $DIR/*
if [ "$PRESERVE_DIR" ]; then
    mv $PRESERVE_DIR/* $DIR || true
    rmdir $PRESERVE_DIR
fi

[ -f $DIR/mediaserver.conf ] && exit 0

if [ $WINDIR ]; then
    DATA_DIR=${DIR/\/c/c:}
else
    DATA_DIR=$DIR
fi

cat > $DIR/mediaserver.conf <<EOF
[General]
appserverPassword=
authKey=@ByteArray(SK_1267cfbb4010058a2c8e5d2abaf917ed)
dataDir=$DATA_DIR
guidIsHWID=0

http-log-level=VERBOSE
logLevel=VERBOSE
logArchiveSize=7
logFile=$DATA_DIR/log/log_file
maxLogFileSize=110485760

lowPriorityPassword=
publicIPEnabled=1
removeDbOnStartup=0
secureAppserverConnection=1
separateGuidForRemoteEC=1
serverGuid={0000000$ID-$PERSONAL_ID-7d56-2bc7-67afae00335c}
systemName=$SYS

EOF

if [[ $EMI ]]; then
cat >> $DIR/mediaserver.conf <<EOF
port=$((7001+ID))
enableMultipleInstances=1

EOF
fi
