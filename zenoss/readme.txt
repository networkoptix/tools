Based on  http://wiki.zenoss.org/Prepare_Remote_Device

=== Start Zenoss docker container ===
1. ssh-keygen -t dsa -f ./zenoss_dsa -q -N ""
2. docker build -t zenoss .
3. docker run -p 1080:80 -d zenoss:latest
NOTE. The first run of the container may take a long time due to zenpack procedure.
You can go into container:
  docker exec -it -u zenoss <CONTAINER NAME> bash
and check zenoss status:
  zenstat status

=== Prepare Zenoss GUI ===

Configuration Properties:
 - zSnmpCommunity = zenoss
 - zKeyPath = ~/.ssh/zenoss_dsa
 - zCommandUsername = zenoss
 - zCommandPassword = <PASSWORD>

=== Prepare Ubuntu Linux host for monitoring ===

1. Install SNMP agent:
   apt-get install snmpd

2. Prepare SNMP config zenoss:
   mv /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.back
   echo "rocommunity zenoss" > /etc/snmp/snmpd.conf

3. Restart SNMP agent:
   service snmpd restart

4. Create zenoss user:
   adduser zenoss (with 'standard' password)

5. Copy zenoss public SSH-key:
   su - zenoss
   cat zenoss_dsa.pub >> ~/.ssh/authorized_keys

6. Add device through Zenoss GUI.

