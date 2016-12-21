#!/bin/bash

#export TASKBOT_DEBUG_MODE=1
cd $HOME/taskbot/devtools/taskbot/instances/windows

screen -wipe
screen -dmS taskbot -t main bash
screen -S taskbot -X screen -t dev_3_0_0 ./run.sh config_dev_3_0_0.py
screen -S taskbot -X screen -t dev_3_0_0_gui ./run.sh config_dev_3_0_0_gui.py
screen -S taskbot -X screen -t release_3_0 ./run.sh config_release_3_0.py
# screen -S taskbot -X screen -t prod_3_0_0 ./run.sh config_prod_3_0_0.py
# screen -S taskbot -X screen -t dev_2_6 ./run.sh config_dev_2_6.py
# screen -S taskbot -X screen -t prod_2_6 ./run.sh config_prod_2_6.py
