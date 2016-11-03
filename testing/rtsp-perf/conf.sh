#!/bin/bash
SERV_DEB=/vagrant/networkoptix-mediaserver.deb
SERVDIR=/opt/networkoptix/mediaserver
SERVCONF=${SERVDIR}/etc/mediaserver.conf
EXT_IF=eth0
INT_IF=eth1

function edconf {
	var=$1
	val="$2"
	if grep -q "^$var" "$SERVCONF"; then
		sed -i 's/^'"$var"'\s*=.*/'"$var=$val/" "$SERVCONF"
	else
		sed -i 's/^\[General\].*/\0\n'"$var=$val/" "$SERVCONF"
	fi
}

function setpw {
	sed -i 's/^appserverPassword\s*=.*/appserverPassword=123/' "$SERVCONF"
}

function rmbase() {
    if [ -n "$1" -a -d "$1" ]; then
        rm "$1"/*.sqlite
        rm -rf "$1/hi_quality"
        rm -rf "$1/low_quality"
    fi
}
