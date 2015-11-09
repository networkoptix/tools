#!/bin/bash
. /vagrant/conf.sh
cp "${SERVCONF}.orig" "$SERVCONF"
edconf removeDbOnStartup 1
# we have to set the password each time!
setpw

