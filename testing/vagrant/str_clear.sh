#!/bin/bash
. /vagrant/conf.sh
# Clears the main storage, passed as $1, and restore the system name
stop networkoptix-mediaserver
rmbase "$1"
rm ${SERVDIR}/var/*.sqlite
edconf removeDbOnStartup 1
#setpw
start networkoptix-mediaserver

