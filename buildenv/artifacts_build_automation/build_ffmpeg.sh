#!/bin/bash

source "../../util/utils.sh"

set -e #< Stop on error.
set -u #< Forbid undefined variables.

declare -r SUPPORTED_TARGETS=( linux_arm32 rpi )
declare -r FFMPEG_VERSION="3.1.9"
declare -r FFMPEG_DEV_ARTIFACT_TARGET="linux"
declare -r FFMPEG_DEV_ARTIFACT="ffmpeg-dev-${FFMPEG_VERSION}"
declare -r GCC_ARTIFACT_TARGET="rpi"
declare -r GCC_ARTIFACT="gcc-4.8.3"

help_callback()
{
    cat \
<<EOF
This script should be used to build ffmpeg artifact.
Prerequisites:
  - Rdep should be on path as "rdep".
  - RDEP_PACKAGES_DIR env var should point to rdep packages.
Usage: run this script directly from devtools repo; current dir doesn't matter.

 $(basename "$0") <options> [--no-rdep] <target> <build-result-dir>

$NX_HELP_TEXT_OPTIONS
EOF
}

# [in] GCC
# [in] FFMPEG_DEV
# [in] RDEP_PACKAGES_DIR
downloadArtifacts()
{
    local -r FFMPEG_DEV_CHECKSUM="763e3c83819bc23f5c3fb24a43a12ac0 *files.md5"

    rm -rf "$GCC"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$GCC_ARTIFACT_TARGET" "$GCC_ARTIFACT"

    rm -rf "$FFMPEG_DEV"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$FFMPEG_DEV_ARTIFACT_TARGET" "$FFMPEG_DEV_ARTIFACT"

    nx_pushd "$RDEP_PACKAGES_DIR/linux/$FFMPEG_DEV_ARTIFACT"

    if [[ $(./test_checksums.sh) != $FFMPEG_DEV_CHECKSUM ]]
    then
        nx_fail "Unexpected checksum in $FFMPEG_DEV_ARTIFACT"
    fi

    nx_popd
}

# [in] GCC
buildOgg()
{
    nx_echo "Building libogg..."

    nx_cd "$FFMPEG_DEV/src/libogg-1.3.3"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    if [[ -f Makefile ]]
    then
        nx_verbose make distclean || true
    fi

    nx_verbose ./configure \
        --host=arm-linux-gnueabihf \
        --prefix=/usr \
        --disable-shared \
        --with-pic

    nx_verbose make -j

    nx_verbose make install DESTDIR="$SYSROOT"
}

# [in] GCC
buildVorbis()
{
    nx_echo "Building libvorbis..."

    nx_cd "$FFMPEG_DEV/src/vorbis-1.3.6"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    if [[ -f Makefile ]]
    then
        nx_verbose make clean
    fi

    nx_verbose cmake \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
        -DCMAKE_C_COMPILER=arm-linux-gnueabihf-gcc \
        -DCMAKE_CXX_COMPILER=arm-linux-gnueabihf-g++ \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DOGG_INCLUDE_DIRS="$SYSROOT/usr/include" \
        -DOGG_LIBRARIES="$SYSROOT/usr/lib" \
        -DCMAKE_SYSTEM_PROCESSOR=arm \
        .

    nx_verbose cmake --build .

    nx_verbose make install DESTDIR="$SYSROOT"
}

# [in] GCC
buildLibVpx()
{
    nx_echo "Building libvpx..."

    nx_cd "$FFMPEG_DEV/src/libvpx-1.7.0"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    export \
        LD=arm-linux-gnueabihf-gcc \
        AR=arm-linux-gnueabihf-ar \
        STRIP=arm-linux-gnueabihf-strip \
        AS=arm-linux-gnueabihf-as \
        CC=arm-linux-gnueabihf-gcc \
        CXX=arm-linux-gnueabihf-c++

    if [[ -f Makefile ]]
    then
        nx_verbose make distclean || true
    fi
    
    nx_verbose ./configure \
        --target=armv7-linux-gcc \
        --prefix=/usr \
        --disable-examples \
        --disable-unit-tests \
        --enable-pic \
        --disable-docs

    nx_verbose make -j

    nx_verbose make install DESTDIR="$SYSROOT"
}

# [in] GCC
buildLame()
{
    nx_echo "Building lame..."

    nx_cd "$FFMPEG_DEV/src/lame-3.99.5"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    if [[ -f Makefile ]]
    then
        nx_verbose make distclean || true
    fi

    nx_verbose ./configure \
        --host=arm-linux-gnueabihf \
        --prefix=/usr \
        --disable-shared \
        --with-pic \
        --enable-static

    nx_verbose make -j

    nx_verbose make install DESTDIR="$SYSROOT"
}

# [in] GCC
buildOpenH264()
{
    nx_echo "Building openh264..."

    nx_cd "$FFMPEG_DEV/src/openh264-1.7.0"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    export CXX=arm-linux-gnueabihf-g++
    export CC=arm-linux-gnueabihf-gcc

    nx_verbose make clean
    nx_verbose make ARCH=arm PREFIX=/usr -j
    nx_verbose make ARCH=arm PREFIX=/usr DESTDIR="$SYSROOT" install-static
}

# [in] GCC
# [in] FFMPEG_DEV 
buildFfmpeg() # ABSOLUTE_DESTINATION_DIR
{
    nx_echo "Building ffmpeg..."

    local -r ABSOLUTE_DESTINATION_DIR="$1"

    nx_cd "$FFMPEG_DEV/src/ffmpeg-$FFMPEG_VERSION"

    local -r SYSROOT="$FFMPEG_DEV/sysroot"

    export PKG_CONFIG_PATH="$SYSROOT/usr/lib/pkgconfig"

    if [[ -f Makefile ]]
    then
        nx_verbose make distclean || true
    fi

    local -r COMMON_OPTIONS=(
        --prefix=/
        --disable-static
        --enable-shared
        --enable-cross-compile
        --cross-prefix="$GCC/bin/arm-linux-gnueabihf-"
        --arch=arm
        --target-os=linux
        --extra-cflags=-fno-omit-frame-pointer
        --extra-cflags=-ggdb1
        --disable-stripping
        --disable-doc
        --enable-encoder=adpcm_g726
        --enable-gray
        --enable-libvorbis
        --enable-libvpx
        --enable-libmp3lame
        --enable-libopenh264
        --enable-neon
        --extra-cflags="-I$SYSROOT/usr/include"
        --extra-cflags="-I$SYSROOT/opt/vc/include"
        --extra-cflags="-I$SYSROOT/opt/vc/include/IL"
        --extra-ldflags="-L$SYSROOT/usr/lib"
        --extra-ldflags="-L$SYSROOT/usr/lib/arm-linux-gnueabihf"
        --extra-ldflags="-L$SYSROOT/opt/vc/lib"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/usr/lib/arm-linux-gnueabihf"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/opt/vc/lib"
        --extra-ldflags="-lstdc++"
    )

    local -r RPI_OPTIONS=(
        --enable-mmal
        --enable-omx
        --enable-omx-rpi
        --disable-mmx
    )

    local options=()
    options+=( "${COMMON_OPTIONS[@]}" )

    if [[ $TARGET == "rpi" ]]
    then
        options+=( "${RPI_OPTIONS[@]}" )
    fi

    nx_verbose ./configure "${options[@]}"

    nx_verbose make -j

    nx_verbose make DESTDIR="$ABSOLUTE_DESTINATION_DIR" install
}

# [in] TARGET
checkTargetArg()
{
    if [[ -z "$TARGET" ]]
    then
        nx_fail "Specify target as an argument."
    fi

    local -i targetIsOk=0
    local t

    for t in "${SUPPORTED_TARGETS[@]}"
    do
        if [[ $t == $TARGET ]]
        then
            targetIsOk=1
            break
        fi
    done

    if (( $targetIsOk != 1 ))
    then
        nx_fail "Unsupported target specified: $TARGET"
    fi
}

# [in] DESTINATION_DIR
checkDestinationDirArg()
{
    if [[ -z $DESTINATION_DIR ]]
    then
        nx_fail "Specify build result dir as an argument."
    fi

    if [[ -d "$DESTINATION_DIR" ]]
    then
        nx_fail "Build result dir already exists."
    fi
}

main()
{
    if [[ -z ${RDEP_PACKAGES_DIR:-}} ]]
    then
        nx_fail "RDEP_PACKAGES_DIR should be defined."
    fi

    if ! which rdep &>/dev/null
    then
        nx_fail "Rdep should be on path as \"rdep\"."
    fi

    if (( $# > 0 )) && [[ $1 == "--no-rdep" ]]
    then
        local -r -i NO_RDEP=1
        shift
    else
        local -r -i NO_RDEP=0
    fi

    local -r TARGET="${1:-}"
    checkTargetArg

    local -r DESTINATION_DIR="${2:-}"
    checkDestinationDirArg


    local -r JOB_COUNT=$(($(cat /proc/cpuinfo | grep "^processor" | wc -l)+1))
    local -r GCC="$RDEP_PACKAGES_DIR/$GCC_ARTIFACT_TARGET/$GCC_ARTIFACT"
    local -r FFMPEG_DEV="$RDEP_PACKAGES_DIR/$FFMPEG_DEV_ARTIFACT_TARGET/$FFMPEG_DEV_ARTIFACT"

    export PATH="$PATH:$GCC/bin"

    if (( $NO_RDEP == 0 ))
    then
        downloadArtifacts
    fi

    #( buildOpenH264 )
    #( buildOgg )
    #( buildVorbis )
    #( buildLibVpx )
    #( buildLame )
    ( buildFfmpeg "$(nx_absolute_path "$DESTINATION_DIR")" )
}

nx_run "$@"
