#!/bin/bash
. /vagrant/fix-hostname.sh "$1"

echo 1 > /proc/sys/net/ipv4/ip_forward
iptables --flush

#iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE --random
#iptables -A FORWARD -i eth0 -o eth2 -m state --state RELATED,ESTABLISHED -j ACCEPT
#iptables -A FORWARD -i eth2 -o eth0 -j ACCEPT

iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE --random
iptables -A FORWARD -i eth1 -o eth2 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth2 -o eth1 -j ACCEPT

