#!/bin/bash -xe

# must be run from junk_shop root directory

docker build -f deploy/Dockerfile -t junk_shop .
