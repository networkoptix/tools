#!/bin/bash

if [[ "$@" == *help ]] || [[ "$@" == -h ]]
then
cat <<END
Clean up mediaservers database and setup default config
Usage: [OPTION=VALUE ...] clear-ms.sh [<hex-id>]
Options:
    DIR config directory to wipe, default $HOME/develop/mediaserver<hex-id>.
    SYS system name, default muskov (the creator).
    EMI set to 1 to enableMultipleInstances=1, port will be also fixed.
    PART clean up partialy, values: log, data.
END
exit 0
fi

set -x -e

ID=${1:-0}
DIR=${DIR:-$HOME/develop/mediaserver$ID}
SYS=${SYS:-muskov}

if [[ "$PART" ]]; then
    [[ "$PART" =~ *l* ]] && rm $DIR/log/*
    [[ "$PART" =~ *d* ]] && rm -r $DIR/data
    exit 0
fi

mkdir -p $DIR
rm -rf $DIR/*
cd $DIR

cat > $DIR/mediaserver.conf <<EOF
[General]
appserverPassword=
authKey=@ByteArray(SK_1267cfbb4010058a2c8e5d2abaf917ed)
dataDir=$DIR
guidIsHWID=0
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
