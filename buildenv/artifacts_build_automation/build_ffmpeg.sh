#!/bin/bash

source "../../util/utils.sh"

set -e #< Stop on error.
set -u #< Forbid undefined variables.

source "build_common.sh"

declare -r SUPPORTED_TARGETS=( linux_arm32 linux_arm64 rpi )
declare -r FFMPEG_VERSION="3.1.9"
declare -r TARGET_ARTIFACT_DEV_ARTIFACT_TARGET="linux"
declare -r TARGET_ARTIFACT_DEV_ARTIFACT="ffmpeg-dev-${FFMPEG_VERSION}"

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
# [in] TARGET_ARTIFACT_DEV
# [in] RDEP_PACKAGES_DIR
downloadArtifacts()
{
    local -r TARGET_ARTIFACT_DEV_CHECKSUM="90ab6287ac1ebe5b6ff517973fd319d7 *files.md5"

    nxDownloadGccArtifact

    rm -rf "$TARGET_ARTIFACT_DEV"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$TARGET_ARTIFACT_DEV_ARTIFACT_TARGET" "$TARGET_ARTIFACT_DEV_ARTIFACT"

    nx_pushd "$RDEP_PACKAGES_DIR/linux/$TARGET_ARTIFACT_DEV_ARTIFACT"

    if [[ $(./test_checksums.sh) != $TARGET_ARTIFACT_DEV_CHECKSUM ]]
    then
        nx_fail "Unexpected checksum in $TARGET_ARTIFACT_DEV_ARTIFACT"
    fi

    nx_popd
}

# [in] GCC
buildOgg()
{
    nx_echo "Building libogg..."

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/libogg-1.3.3"

    local -r AUTOCONF_OPTIONS=(
        --host="${GCC_PREFIX%-}"
        --prefix=/usr
        --disable-shared
        --with-pic
    )

    nxAutotoolsBuild
}

# [in] GCC
buildVorbis()
{
    nx_echo "Building libvorbis..."

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/vorbis-1.3.6"

    local -r CMAKE_GEN_OPTIONS=(
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        -DCMAKE_C_COMPILER="${GCC_PREFIX}gcc"
        -DCMAKE_CXX_COMPILER="${GCC_PREFIX}g++"
        -DCMAKE_INSTALL_PREFIX=/usr
        -DOGG_INCLUDE_DIRS="$SYSROOT/usr/include"
        -DOGG_LIBRARIES="$SYSROOT/usr/lib"
        -DCMAKE_SYSTEM_PROCESSOR="${ARCH_BY_TARGET[$TARGET]}"
    )

    nxCmakeBuild
}

# [in] GCC
buildLibVpx()
{
    nx_echo "Building libvpx..."

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/libvpx-1.7.0"

    local -r TOOLCHAIN_PREFIX="${GCC_PREFIX}"

    local -rA TARGET_OPTION_BY_TARGET=(
        [linux_arm32]=armv7-linux-gcc
        [rpi]=armv7-linux-gcc
        [linux_arm64]=arm64-linux-gcc
    )

    local -r AUTOCONF_OPTIONS=(
        --target="${TARGET_OPTION_BY_TARGET[$TARGET]}"
        --prefix=/usr
        --disable-examples
        --disable-unit-tests
        --enable-pic
        --disable-docs
    )
    
    nxAutotoolsBuild
}

# [in] GCC
buildLame()
{
    nx_echo "Building lame..."
    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/lame-3.100"

    local -r AUTOCONF_OPTIONS=(
        --host="${GCC_PREFIX%-}"
        --prefix=/usr
        --disable-shared
        --with-pic
        --enable-static
    )

    nxAutotoolsBuild
}

# [in] GCC
buildOpenH264()
{
    nx_echo "Building openh264..."

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/openh264-1.7.0"

    nxExportToolchainMediatorVars "${GCC_PREFIX}"

    nxMake ARCH="${ARCH_BY_TARGET[$TARGET]}" PREFIX=/usr
    nxMake ARCH="${ARCH_BY_TARGET[$TARGET]}" PREFIX=/usr DESTDIR="$SYSROOT" install-static
}

# [in] GCC
# [in] TARGET_ARTIFACT_DEV 
buildFfmpeg() # ABSOLUTE_DESTINATION_DIR
{
    nx_echo "Building ffmpeg..."

    local -r ABSOLUTE_DESTINATION_DIR="$1"

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/ffmpeg-$FFMPEG_VERSION"

    local -r COMMON_OPTIONS=(
        --prefix=/
        --disable-static
        --enable-shared
        --enable-cross-compile
        --cross-prefix="${GCC_PREFIX}"
        --arch="${ARCH_BY_TARGET[$TARGET]}"
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
        --extra-ldflags="-L$SYSROOT/usr/lib"
        --extra-ldflags="-L$SYSROOT/usr/lib/${GCC_PREFIX%-}"
        --extra-ldflags="-L$SYSROOT/opt/vc/lib"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/usr/lib"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/usr/lib/${GCC_PREFIX%-}"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/opt/vc/lib"
        --extra-ldflags="-lstdc++"
    )

    local -r RPI_OPTIONS=(
        --enable-mmal
        --enable-omx
        --enable-omx-rpi
        --disable-mmx
    )

    local -r LINUX_ARM64_OPTIONS=(
        --pkg-config=pkg-config
    )

    local AUTOCONF_OPTIONS=()
    AUTOCONF_OPTIONS+=( "${COMMON_OPTIONS[@]}" )

    case "$TARGET" in
        rpi)
        AUTOCONF_OPTIONS+=( "${RPI_OPTIONS[@]}" )
        ;;
        linux_arm64)
        AUTOCONF_OPTIONS+=( "${LINUX_ARM64_OPTIONS[@]}" )
        ;;
        *)
        ;;
    esac

    DESTDIR="$ABSOLUTE_DESTINATION_DIR" V=1 nxAutotoolsBuild
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

    local -r BUILD_ROOT_DIR=$(mktemp -d -p "${TMPDIR:-/tmp}" --suffix=-ffmpeg_build)

    if [[ -z "${BUILD_ROOT_DIR}" ]]
    then
        nx_fail "Can't create temporary directory."
    fi

    warnTempBuildDir()
    {
        (( "$RESULT" == 0 )) && return

        nx_echo "The temporary build dir '${BUILD_ROOT_DIR}' is retained for the problem investigations."
    }

    NX_EXIT_HOOKS+=( warnTempBuildDir )

    mkdir -p "$BUILD_ROOT_DIR/sysroot"
    local -r SYSROOT="$BUILD_ROOT_DIR/sysroot"

    local -r JOB_COUNT=$(($(cat /proc/cpuinfo | grep "^processor" | wc -l)+1))

    nxInitToolchain

    local -r TARGET_ARTIFACT_DEV="$RDEP_PACKAGES_DIR/$TARGET_ARTIFACT_DEV_ARTIFACT_TARGET/$TARGET_ARTIFACT_DEV_ARTIFACT"

    if (( $NO_RDEP == 0 ))
    then
        downloadArtifacts
    fi

    cp -af "$TARGET_ARTIFACT_DEV/src/"sysroot/* "$SYSROOT/"

    ( buildOpenH264 )
    ( buildOgg )
    ( buildVorbis )
    ( buildLibVpx )
    ( buildLame )
    ( buildFfmpeg "$(nx_absolute_path "$DESTINATION_DIR")" )

    rm -rf "$BUILD_ROOT_DIR"
}

nx_run "$@"

