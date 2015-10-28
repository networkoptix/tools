#!/bin/bash
# make it non-executable to disable htpd start when eth0 goes up
chmod -x /etc/network/if-up.d/ntpdate
ifup eth0

