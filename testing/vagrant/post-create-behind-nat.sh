#!/bin/bash
. /vagrant/conf.sh

stop networkoptix-mediaserver

echo Disabling eth0
ifdown eth0
route add default gw 192.168.110.2

setpw
start networkoptix-mediaserver

