#!/bin/bash

set -e

if [[ $# > 0 ]]
then
    BUILD_DIRECTORY=$1
else
    BUILD_DIRECTORY=../verify_globs-build
fi

cmake -B${BUILD_DIRECTORY} . -DCMAKE_BUILD_TYPE=Release
cmake --build ${BUILD_DIRECTORY}
