#!/bin/bash -xe

. ~/venv/bin/activate

cd $(dirname $0)/..

export FLASK_APP=junk_shop/webapp.py
export FLASK_DEBUG=1

flask run
