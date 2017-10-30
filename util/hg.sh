#!/bin/bash

set -e -x

COMMAND=$1
shift

case "$COMMAND" in
    share|sh)
        hg share "$@"
        cp "$1/.hg/hgrc" "$2/.hg/hgrc"
        ;;
    *)
        set +x
        echo Unknown command "$COMMAND" >&2
        exit 1
        ;;
esac
