#!/bin/bash
# Searches who is possible responsible for ut fail
# Usage example:
#    ut_blame.sh "QnStoppableAsync, SingleAsync"
if [ -z "$1" ]; then
    echo Nothing to find!
    echo Usage example: $0 "QnStoppableAsync, SingleAsync"
    exit 1
fi
grep -rI "$1" | tr ':' '\n' | head -1 | xargs hg annotate -u | grep "$1" | tr ':' '\n' | head -1
