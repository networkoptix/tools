#!/bin/bash
. /vagrant/conf.sh
# Clears the main and the backaup storages, passed as $1 and $1
function rmbase() {
    if [ -n "$1" -a -d "$1" ]; then
        rm "$1"/*.sqlite
        rm -rf "$1/hi_quality"
        rm -rf "$1/low_quality"
    fi
}
stop networkoptix-mediaserver
rmbase "$1"
rmbase "$2"
edconf removeDbOnStartup 1
setpw
start networkoptix-mediaserver

