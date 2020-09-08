# Description
Docker image for workflow police bot responsible for Version Checking automation. 
More info: https://networkoptix.atlassian.net/wiki/spaces/SD/pages/1486749741/Automation+Workflow+Police+bot

# Requirements
In order to proper use, several host directories have to be mounted inside container:
* .ssh directory with keys for access to the repo:/home/workflow-police/.ssh
* directory with config file for workflow_police:/etc/workflow-police/

# Parameters
* *config_file* yaml file with configuration options, example: https://gitlab.lan.hdw.mx/dev/tools/-/blob/master/workflow_police/config.yaml
* *--log-level* {CRITICAL,FATAL,ERROR,WARN,WARNING,INFO,DEBUG,NOTSET} level for logging, default INFO
* *--dry-run* Run single iteration, don't change any states

The directories must have proper UID & GID, default 1000:1000,
the UID & GID can be configured at image build time.

# Example
Run in docker:
`docker run --rm -it -v ~/.config/workflow-police/:/etc/workflow-police/ -v ~/.ssh:/home/workflow-police/.ssh workflow_police /etc/workflow-police/config.yaml --log-level DEBUG`
