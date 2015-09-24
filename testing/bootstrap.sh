#!/bin/sh
_DEB=/vagrant/networkoptix-mediaserver.deb
_CONF=/opt/networkoptix/mediaserver/etc/mediaserver.conf

. /vagrant/fix-hostname.sh $1
DEBIAN_FRONTEND=noninteractive dpkg -i --force-depends "$_DEB"
#apt-get install -f --yes --allow-unauthenticated

stop networkoptix-mediaserver
#echo '...Before:'
#cat "$_CONF"
sed -i 's/^appserverPassword\s*=.*/appserverPassword=123/' "$_CONF"
if grep -q '^systemName' "$_CONF"; then
	sed -i 's/^systemName\s*=.*/systemName=functesting/' "$_CONF"
else
	sed -i 's/^\[General\].*/\0\nsystemName=functest/' "$_CONF"
fi
#echo '...After:'
#cat "$_CONF"
start networkoptix-mediaserver


