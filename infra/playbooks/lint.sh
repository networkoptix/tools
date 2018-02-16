#!/usr/bin/env bash
source ./.venv/bin/activate \
&& ansible-lint ./*.yml
