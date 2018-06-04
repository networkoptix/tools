=========================================================
How to connect remote (Burbank) node/slave to jenkins in Moscow
=========================================================

Currently, Burbank does not have common intranet network with Moscow.
So, to connect jenkins nodes to it, we use ssh 'ProxyJump' feature.

For example, to connect host 1.1.1.1, having alias scalability1:

1. Configure ssh on jenkins master, so that 'ssh scalability1' will connect to target host 1.1.1.1
   If master does not have direct access to 1.1.1.1, configure ~/.ssh/config with ProxyJump thru la.hdw.mx.
   Jenkins master will require account on la.hdw.mx for this to work.
2. Put script burbank-scalability-agent.sh in this directory to jenkins master,
   for example, to /var/jenkins_home/scripts/launch_agent.sh
3. Create jenkins node with the following parameters:
  1. Launch method: Launch agent via execution of command on the master.
  2. Launch command: /var/jenkins_home/scripts/launch_agent.sh scalability1
  3. Availability: Keep this agent online as much as possible.


Also CI jobs require connection to junk-shop postgres database.
For them burbank-scalability-agent.sh is proxying postgres port from slave back to master using -R ssh option:

| ssh -R 5432:$JUNK_SHOP_DB_HOST:5432

so, when configuring these jobs, juhk-shop db host must be specified as 'localhost', which will be proxied to real one.
