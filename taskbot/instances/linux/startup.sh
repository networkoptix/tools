#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/linux

. $HOME/.bashrc

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t vms_3.0 ./run.sh config_vms_3_0.py
screen -S taskbot -X screen -t vms_3.1 ./run.sh config_vms_3_1.py
screen -S taskbot -X screen -t vms_3.1_release ./run.sh config_vms_3_1_release.py
screen -S taskbot -X screen -t vms_3.1.2 ./run.sh config_vms_3_1_2.py
screen -S taskbot -X screen -t vms_3.1.2_dev ./run.sh config_vms_3_1_2_dev.py
screen -S taskbot -X screen -t vms_3.1.2_gui ./run.sh config_vms_3_1_2_gui.py
screen -S taskbot -X screen -t vms_3.2_dev ./run.sh config_vms_3_2_dev.py
screen -S taskbot -X screen -t cloud_dev ./run.sh config_cloud_dev.py
screen -S taskbot -X screen -t cloud_17.1 ./run.sh config_cloud_17_1.py
screen -S taskbot -X screen -t default ./run.sh config_default.py
screen -S taskbot -X screen -t slow_vms_3.0 ./slow.sh config_vms_3_0.py
screen -S taskbot -X screen -t slow_vms_3.1 ./slow.sh config_vms_3_1.py
screen -S taskbot -X screen -t slow_vms_3.1.2 ./slow.sh config_vms_3_1_2.py
screen -S taskbot -X screen -t slow_vms_3.1.2_dev ./slow.sh config_vms_3_1_2_dev.py
screen -S taskbot -X screen -t slow_vms_3.2_dev ./slow.sh config_vms_3_2_dev.py
screen -S taskbot -X screen -t nx1_vms_3.0 sh -c "cd $HOME/taskbot/devtools/taskbot/instances/nx1 && ./run.sh config_vms_3_0.py"
screen -S taskbot -X screen -t nx1_vms_3.1.2_dev sh -c "cd $HOME/taskbot/devtools/taskbot/instances/nx1 && ./run.sh config_vms_3_1_2_dev.py"
