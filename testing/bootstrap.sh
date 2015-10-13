#!/bin/sh
. /vagrant/conf.sh
. /vagrant/fix-hostname.sh $1
DEBIAN_FRONTEND=noninteractive dpkg -i --force-depends "$SERV_DEB"
#apt-get install -f --yes --allow-unauthenticated

# We need it stopped for some tests
service ntp stop

stop networkoptix-mediaserver
#echo '...Before:'
#cat "$SERVCONF"
sed -i 's/^appserverPassword\s*=.*/appserverPassword=123/' "$SERVCONF"
if grep -q '^systemName' "$SERVCONF"; then
	sed -i 's/^systemName\s*=.*/systemName=functesting/' "$SERVCONF"
else
	sed -i 's/^\[General\].*/\0\nsystemName=functest/' "$SERVCONF"
fi
#echo '...After:'
#cat "$SERVCONF"
start networkoptix-mediaserver


