# Description
Docker image for Workflow Robocat Gitlab Bot who is designated to automate the Merge Request merging routine and enforce some workflow rules.. 
More info: https://networkoptix.atlassian.net/wiki/spaces/SD/pages/1486749741/Automation+Workflow+Police+bot

# Requirements
`python-gitlab.cfg` should be mounted to `/etc/python-gitlab.cfg` in container.
Example maybe found at workflow_police/robocat/python-gitlab.cfg.example.

The directories must have proper UID & GID, default 1000:1000,
the UID & GID can be configured at image build time.

# Parameters
Run: `./robocat.app --help`

# Recommended example
Run in docker:
`docker run -it -v /etc/python-gitlab.cfg:/etc/python-gitlab.cfg workflow-robocat -p 2 --log-level=DEBUG`
