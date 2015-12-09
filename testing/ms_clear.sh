#!/bin/bash
. /vagrant/conf.sh
# Clears the main and the backaup storages, passed as $1 and $1
stop networkoptix-mediaserver
rmbase "$1"
edconf removeDbOnStartup 1
edconf systemName functesting
setpw
start networkoptix-mediaserver

