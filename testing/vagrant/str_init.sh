#!/bin/bash
. /vagrant/conf.sh
cp "${SERVCONF}.orig" "$SERVCONF"
edconf removeDbOnStartup 1
edconf logLevel DEBUG2
edconf http-log-level DEBUG2
# we have to set the password each time!
#setpw
