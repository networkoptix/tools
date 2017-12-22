#!/bin/bash

set -e -x

COMMAND=$1
shift

case "$COMMAND" in
    share|sh)
        hg share "$@"
        cp "$1/.hg/hgrc" "$2/.hg/hgrc"
        ;;
    pull)
        hg shelve
        hg pull "$@" --rebase
        hg unshelve
        ;;
    *)
        set +x
        echo "Unknown command '$COMMAND', use:" >&2
        echo "    share [source] [new]  - Share with copy of hgrc." >&2
        echo "    pull                  - Pull and update like git does." >&2
        exit 1
        ;;
esac
