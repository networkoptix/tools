#!/bin/bash
. /vagrant/conf.sh
. /vagrant/fix-hostname.sh $1
echo Installing $SERV_DEB
DEBIAN_FRONTEND=noninteractive dpkg -i --force-depends "$SERV_DEB"
#apt-get install -f --yes --allow-unauthenticated

#if [ "$2" == "nontp" ]; then
#    # We need it stopped for some tests
#    echo '*** STOPPING NTPD ***'
#    service ntp stop
#fi

stop networkoptix-mediaserver
#echo '...Before:'
#cat "$SERVCONF"
#setpw
nxedconf appserverPassword ''
nxedconf systemName functesting
nxedconf removeDbOnStartup 1
cp "$SERVCONF" "${SERVCONF}.orig"
#echo '...After:'
#cat "$SERVCONF"
#start networkoptix-mediaserver


