#!/bin/bash
. /vagrant/conf.sh
GWADDR=$1

stop networkoptix-mediaserver

echo Disabling eth0
ifdown eth0
route add default gw $GWADDR

#setpw
start networkoptix-mediaserver

