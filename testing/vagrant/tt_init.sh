#!/bin/bash
# Time test initialisation. $1 has to be unix timestamp
. /vagrant/conf.sh

edconf removeDbOnStartup 1
# we have to set the password each time!
setpw

###edconf logLevel DEBUG2

ifdown $EXT_IF > /dev/null
date --set=@$1

