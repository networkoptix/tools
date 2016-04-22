*Valgrind scripts for Mediaserver*

**Basic usadge**

1. Copy `dev_tools/valgrind` to the target machine or `hg clone dev_tools`
2. Install valgrind e.g. `sudo apt-get install valgrind`
3. Run from any directory `sudo dev_tools/valgrind/run-ms.sh [tool]`
    supported tools: memcheck, dhat, massif, callgrind
4. Terminate it after some time by Ctrl+C
5. Look into `dev_tools/valgrind/valgrind-ms.out.*` files


**Running as service**

1. Install service huck `sudo dev_tools/valgrind/huck-service-ms.sh [tool]`
2. Start or restart service `sudo service networkoptix restart`
3. Stop service after some time `sudo service networkoptix stop`
4. Look into `/opt/networkoptix/mediaserver/bin/valgrind-ms.out.*` files

