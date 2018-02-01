#!/bin/bash
set -e
set -x
INIT_FOLDER=$(pwd)
CUSTOMIZATION=$1
OPT_FOLDERS="$(ls /opt | xargs)"
if [ -z "$CUSTOMIZATION" ]
    then echo "You forget to enter customization name"
    exit
fi
if pgrep mediaserver
    then
    pkill -9 mediaserver
fi
if pgrep -f run_watchdog
    then
    pkill -9 -f run_watchdog
fi
for FOLDER in $OPT_FOLDERS
do
    if ls /opt/$FOLDER | grep mediaserver
        then echo "/opt/$FOLDER is customization folder"
        rm -rf /opt/$FOLDER
    else
        echo "/opt/$FOLDER isn't customization folder"
    fi
done
rm -f /etc/init.d/*-mediaserver
mkdir -p "$INIT_FOLDER"/$CUSTOMIZATION
dpkg -l |grep unzip
unzip -o "$INIT_FOLDER"/$CUSTOMIZATION*.zip -d "$INIT_FOLDER"/$CUSTOMIZATION/
chmod +x "$INIT_FOLDER"/$CUSTOMIZATION/install.sh
"$INIT_FOLDER"/$CUSTOMIZATION/install.sh
rm -rf "$INIT_FOLDER"/$CUSTOMIZATION
