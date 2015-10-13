#!/bin/bash
. /vagrant/conf.sh

sed -i 's/^removeDbOnStartup\s*=.*/removeDbOnStartup=1/' "$SERVCONF"
# we have to set the password it each time!
sed -i 's/^appserverPassword\s*=.*/appserverPassword=123/' "$SERVCONF"
date -s "$1"

