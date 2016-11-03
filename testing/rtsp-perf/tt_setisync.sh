#!/bin/bash
echo configuring inet sync
. /vagrant/conf.sh

ifdown $EXT_IF > /dev/null
date --set=@$1

edconf removeDbOnStartup 1

# values should be equal to INET_SYNC_TIMEOUT in timetest.py
edconf ecInternetSyncTimePeriodSec 15
edconf ecMaxInternetTimeSyncRetryPeriodSec 15

# we have to set the password each time!
setpw

#cat $SERVCONF
