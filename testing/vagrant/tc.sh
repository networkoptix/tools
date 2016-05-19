#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export LD_LIBRARY_PATH=`dirname $DIR`/lib
export VMS_PLUGIN_DIR=`dirname $DIR`/lib/plugins

$DIR/testcamera "$@"
