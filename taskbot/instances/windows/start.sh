#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/windows

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t vms_3.0 ./run.sh config_vms_3_0.py
screen -S taskbot -X screen -t cloud_dev ./run.sh config_cloud_dev.py
screen -S taskbot -X screen -t default ./run.sh config_default.py
screen -S taskbot -X screen -t vms_3.1_gui ./run.sh config_vms_3_1_gui.py
screen -S taskbot -X screen -t vms_3.1_dev ./run.sh config_vms_3_1_dev.py
