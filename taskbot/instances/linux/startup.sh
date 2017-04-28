#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/linux

. $HOME/.bash_profile

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t dev_3.0.0 ./run.sh config_dev_3_0_0.py
screen -S taskbot -X screen -t dev_3.0.0_gui ./run.sh config_dev_3_0_0_gui.py
screen -S taskbot -X screen -t release_3.0 ./run.sh config_release_3_0.py
screen -S taskbot -X screen -t cloud_dev ./run.sh config_cloud_dev.py
screen -S taskbot -X screen -t default ./run.sh config_default.py
screen -S taskbot -X screen -t prod_3.0.0 ./run.sh config_prod_3_0_0.py
screen -S taskbot -X screen -t vms_3.1_gui ./run.sh config_vms_3_1_gui.py
screen -S taskbot -X screen -t vms_3.1_dev ./run.sh config_vms_3_1_dev.py
screen -S taskbot -X screen -t slow_dev_3.0.0 ./slow.sh config_dev_3_0_0.py
screen -S taskbot -X screen -t slow_vms_3.1_dev ./slow.sh config_vms_3_1_dev.py
screen -S taskbot -X screen -t slow_default ./slow.sh config_default.py
cd $HOME/taskbot/devtools/taskbot/instances/nx1
screen -S taskbot -X screen -t nx1_dev_3.0.0 ./run.sh config_dev_3_0_0.py
