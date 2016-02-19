#!/bin/bash
# make it non-executable to disable ntpd start when eth0 goes up
chmod -x /etc/network/if-up.d/ntpdate
ifup eth0

