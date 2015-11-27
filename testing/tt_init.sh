#!/bin/bash
. /vagrant/conf.sh

edconf removeDbOnStartup 1
# we have to set the password each time!
setpw

###edconf logLevel DEBUG2

ifdown $EXT_IF > /dev/null
date --set=@$1

