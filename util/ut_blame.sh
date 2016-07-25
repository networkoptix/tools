#!/bin/bash
# Searches who is possible responsible for ut fail
# Usage example:
#    ut_blame.sh "QnStoppableAsync, SingleAsync"
grep -rI "$1" | tr ':' '\n' | head -1 | xargs hg annotate -u | grep "$1" | tr ':' '\n' | head -1
