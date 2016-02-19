#!/bin/bash
. /vagrant/conf.sh
# Clears the main and the backaup storages, passed as $1 and $2
stop networkoptix-mediaserver
rmbase "$1"
rmbase "$2"
edconf removeDbOnStartup 1
setpw
start networkoptix-mediaserver

