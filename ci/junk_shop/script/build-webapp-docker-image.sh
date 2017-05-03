#!/bin/bash -xe

# must be run from junk_shop root directory
cd $(dirname $0)/..

docker build -f deploy/Dockerfile -t junk_shop .
