#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/windows

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t vms_3.0 ./run.sh config_vms_3_0.py
screen -S taskbot -X screen -t vms_3.1 ./run.sh config_vms_3_1.py
screen -S taskbot -X screen -t vms_3.1_release ./run.sh config_vms_3_1_release.py
screen -S taskbot -X screen -t vms_3.1.1_release ./run.sh config_vms_3_1_1_release.py
screen -S taskbot -X screen -t cloud_dev ./run.sh config_cloud_dev.py
screen -S taskbot -X screen -t cloud_17.1 ./run.sh config_cloud_17_1.py
screen -S taskbot -X screen -t cloud_17.2 ./run.sh config_cloud_17_2.py
