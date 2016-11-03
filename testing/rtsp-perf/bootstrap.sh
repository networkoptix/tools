#!/bin/bash
. /vagrant/conf.sh
. /vagrant/fix-hostname.sh $1
echo Installing $SERV_DEB
DEBIAN_FRONTEND=noninteractive dpkg -i --force-depends "$SERV_DEB"
#apt-get install -f --yes --allow-unauthenticated

# We need it stopped for some tests
service ntp stop

stop networkoptix-mediaserver
#echo '...Before:'
#cat "$SERVCONF"
setpw
edconf systemName functesting
cp "$SERVCONF" "${SERVCONF}.orig"
#echo '...After:'
#cat "$SERVCONF"
start networkoptix-mediaserver


