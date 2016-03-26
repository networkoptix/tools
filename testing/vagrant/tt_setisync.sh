#!/bin/bash
# Turns on inet time syncronisation and prepare for teesting it
echo configuring inet sync
. /vagrant/conf.sh

ifdown $EXT_IF > /dev/null
date --set=@$1

nxedconf removeDbOnStartup 1

# values should be equal to INET_SYNC_TIMEOUT in timetest.py
nxedconf ecInternetSyncTimePeriodSec 15
nxedconf ecMaxInternetTimeSyncRetryPeriodSec 15

# we have to set the password each time!
#setpw

#cat $SERVCONF
