#!/usr/bin/env bash

[[ ! -d "env" ]] && printf "Creating virtualenv named 'env'\n\n" && virtualenv env --python=python3

. ./env/bin/activate

pip install -r requirements.txt
