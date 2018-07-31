#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs Mediaserver with comfiguration over run.sh
Usage: [OPTION=VALUE ...] $0 COMMAND
Options:
    C - customization, default networkptix
    B - backup directory
Commands:
    d, disable - stops service and remove from autostart
    c, clean - remove data directory incuding daabase
    b, backup - backup database to
    r, restore - restore database
END
exit 0
fi

set -e -x

CUSTOMIZATION=${C:-networkoptix}
BACKUP=${B:-$HOME/develop/backup/$CUSTOMIZATION}

if [ $(whoami) != root ]; then
    C=$CUSTOMIZATION B=$BACKUP sudo -E "$0" "$@"
    exit $?
fi

SERVICE="${CUSTOMIZATION}-mediaserver"
DIRECTORY="/opt/$CUSTOMIZATION/mediaserver"

COMMAND="$1"
shift

function stop_service() {
    service $SERVICE stop
}

function start_service() {
    service $SERVICE start
    for i in {1..10}; do
        curl 127.0.0.1:7001/api/moduleInformation && return 0
        sleep 1
    done
    return 1
}

function disable() {
    systemctl disable ${SERVICE}.service
    echo manual > /etc/init/${SERVICE}.override
    service $SERVICE status
    exit 0
}

function clean() {
    rm -r "$DIRECTORY"/var/*
}

function backup() {
    rm -rf "$BACKUP"
    mkdir -p "$BACKUP"
    cp "$DIRECTORY"/var/*.sqlite "$BACKUP"/
}

function restore() {
    [ -d "$BACKUP" ]
    clean
    cp -r "$BACKUP"/* "$DIRECTORY"/var/
}

stop_service
case $COMMAND in
    d|disable|s|stop) disable "$@" ;;
    c|clean) clean "$@" ;;
    b|backup) backup "$@" ;;
    r|restore) restore "$@" ;;
esac
start_service
