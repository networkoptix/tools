#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/linux

. $HOME/.bash_profile

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t dev_3_0_0 ./run.sh config_dev_3_0_0.py
screen -S taskbot -X screen -t dev_3_0_0_gui ./run.sh config_dev_3_0_0_gui.py
screen -S taskbot -X screen -t release_3_0 ./run.sh config_release_3_0.py
screen -S taskbot -X screen -t prod_3_0_0 ./run.sh config_prod_3_0_0.py
screen -S taskbot -X screen -t dev_3_0_0_cloud ./run.sh config_dev_3_0_0_cloud.py
screen -S taskbot -X screen -t prod_3_0_0 ./run.sh config_default.py
