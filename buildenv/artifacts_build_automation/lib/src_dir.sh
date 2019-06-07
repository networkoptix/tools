#!/bin/bash

prepareSources() # PKG_SRC_DIR
{
    local -r PKG_NAME=$(basename "$1")
    local -r PKG_SRC_DIR="$1"
    local -r BUILD_DIR="${BUILD_ROOT_DIR}/$PKG_NAME"

    cp -af "$PKG_SRC_DIR" "$BUILD_ROOT_DIR/"

    nx_cd "$BUILD_DIR"

    if ls "$FFMPEG_DEV/src/patches/$PKG_NAME"-* &>/dev/null
    then
        for patch in "$FFMPEG_DEV/src/patches/$PKG_NAME"-*
        do
            nx_verbose patch -Np1 -i "$patch"
        done
    fi
}
