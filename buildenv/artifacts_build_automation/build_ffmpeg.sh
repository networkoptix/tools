#!/bin/bash

set -e #< Stop on error.
set -u #< Forbid undefined variables.

source "../../util/utils.sh"
source "build_common.sh"

declare -r SUPPORTED_TARGETS=( linux_x64 linux_arm32 linux_arm64 rpi )
declare -r FFMPEG_VERSION="3.1.9"
declare -r DEV_ARTIFACT_PLATFORM="linux"
declare -r DEV_ARTIFACT_NAME="ffmpeg-dev-${FFMPEG_VERSION}"

help_callback()
{
    cat \
<<EOF
Builds ffmpeg artifact from sources taken from the dedicated rdep artifact.

Prerequisites:
  - Rdep should be on path as "rdep" (not required if --no-rdep is specified).
  - RDEP_PACKAGES_DIR env var should point to rdep packages.
  
Usage: run this script directly from devtools repo; current dir doesn't matter.

 $(basename "$0") <options> [--no-rdep] <target> <destination-dir>

If --no-rdep is specified, required artifacts will not be synced via rdep.

Here <target> is one of: ${SUPPORTED_TARGETS[*]}

$NX_HELP_TEXT_OPTIONS
EOF
}

# [in] GCC
# [in] DEV_ARTIFACT
# [in] RDEP_PACKAGES_DIR
downloadArtifacts()
{
    local -r DEV_ARTIFACT_CHECKSUM="67ea726ddb8ab84b8e9202aaea5ab124 *files.md5"

    nxDownloadGccArtifact

    nx_verbose rm -rf "$DEV_ARTIFACT"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$DEV_ARTIFACT_PLATFORM" "$DEV_ARTIFACT_NAME"

    nx_pushd "$DEV_ARTIFACT"

    local -r checksumCalculated=$(./test_checksums.sh)

    if [[ $(./test_checksums.sh) != $DEV_ARTIFACT_CHECKSUM ]]
    then
        nx_fail "Unexpected checksum in $DEV_ARTIFACT:" \
            "Expected: $DEV_ARTIFACT_CHECKSUM" \
            "Actual: $checksumCalculated"
    fi

    nx_popd
}

# [in] DEV_ARTIFACT
# [in] SYSROOT
installSysroot()
{
    cp -a "$GCC_ARTIFACT_PATH/${GCC_PREFIX%-}/sysroot" "$SYSROOT"

    if [[ $TARGET == "rpi" ]]
    then
        cp -a "$DEV_ARTIFACT/src/rpi-precompiled-files"/* "$SYSROOT"/
    fi
}

# [in] GCC
# [in] DEV_ARTIFACT
buildOgg()
{
    nx_echo "Building libogg..."

    nxPrepareSources "$DEV_ARTIFACT/src/libogg-1.3.3"

    local -r AUTOCONF_OPTIONS=(
        --host="${GCC_PREFIX%-}" #< Make host from gcc prefix by stripping trailing hyphen.
        --prefix=/usr
        --disable-shared
        --with-pic
    )

    nxAutotoolsBuild
}

# [in] GCC
# [in] DEV_ARTIFACT
buildAlsaLib()
{
    nx_echo "Building alsa-lib..."

    nxPrepareSources "$DEV_ARTIFACT/src/alsa-lib-1.1.9"

    local -r AUTOCONF_OPTIONS=(
        --host="${GCC_PREFIX%-}" #< Make host from gcc prefix by stripping trailing hyphen.
        --prefix=/usr
    )

    export LD="${GCC_PREFIX}ld"

    nxAutotoolsBuild 
}

# [in] GCC
# [in] DEV_ARTIFACT
# [in] SYSROOT
buildVorbis()
{
    nx_echo "Building libvorbis..."

    nxPrepareSources "$DEV_ARTIFACT/src/vorbis-1.3.6"

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
# [in] DEV_ARTIFACT
buildLibVpx()
{
    nx_echo "Building libvpx..."

    nxPrepareSources "$DEV_ARTIFACT/src/libvpx-1.7.0"

    local -r TOOLCHAIN_PREFIX="${GCC_PREFIX}"

    local -rA TARGET_OPTION_BY_TARGET=(
        [linux_x64]=x86_64-linux-gcc
        [linux_arm32]=armv7-linux-gcc
        [rpi]=armv7-linux-gcc
        [linux_arm64]=arm64-linux-gcc
    )

    local -r COMMON_OPTIONS=(
        --target="${TARGET_OPTION_BY_TARGET[$TARGET]}"
        --prefix=/usr
        --disable-examples
        --disable-unit-tests
        --enable-pic
        --disable-docs
    )

    local -r LINUX_X64_OPTIONS=(
        --as=yasm
    )

    local AUTOCONF_OPTIONS=()
    AUTOCONF_OPTIONS+=( "${COMMON_OPTIONS[@]}" )

    if [[ $TARGET == linux_x64 ]]
    then
        AUTOCONF_OPTIONS+=( "${LINUX_X64_OPTIONS[@]}" )
    fi

    nxAutotoolsBuild
}

# [in] GCC
# [in] DEV_ARTIFACT
buildLame()
{
    nx_echo "Building lame..."
    nxPrepareSources "$DEV_ARTIFACT/src/lame-3.100"

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
# [in] DEV_ARTIFACT
# [in] SYSROOT
buildOpenH264()
{
    nx_echo "Building openh264..."

    nxPrepareSources "$DEV_ARTIFACT/src/openh264-1.7.0"

    nxExportToolchainMediatorVars "${GCC_PREFIX}"

    export >.env

    nxMake ARCH="${ARCH_BY_TARGET[$TARGET]}" PREFIX=/usr
    nxMake ARCH="${ARCH_BY_TARGET[$TARGET]}" PREFIX=/usr DESTDIR="$SYSROOT" install-static
}

# [in] GCC
# [in] DEV_ARTIFACT 
# [in] SYSROOT
buildFfmpeg() # ABSOLUTE_DESTINATION_DIR
{
    nx_echo "Building ffmpeg..."

    local -r ABSOLUTE_DESTINATION_DIR="$1"

    nxPrepareSources "$DEV_ARTIFACT/src/ffmpeg-$FFMPEG_VERSION"

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
        --enable-postproc
        --enable-libvorbis
        --enable-libvpx
        --enable-libmp3lame
        --enable-libopenh264
        --extra-cflags="-I$SYSROOT/usr/include"
        --extra-ldflags="-L$SYSROOT/usr/lib"
        --extra-ldflags="-L$SYSROOT/usr/lib"
        --extra-ldflags="-L$SYSROOT/usr/lib/${GCC_PREFIX%-}"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/usr/lib"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/usr/lib/${GCC_PREFIX%-}"
        --extra-ldflags="-lstdc++"
    )

    local -r RPI_OPTIONS=(
        --enable-mmal
        --enable-omx
        --enable-omx-rpi
        --disable-mmx
        --enable-neon
        --extra-cflags="-I$SYSROOT/opt/vc/include"
        --extra-cflags="-I$SYSROOT/opt/vc/include/IL"
        --extra-ldflags="-L$SYSROOT/opt/vc/lib"
        --extra-ldflags="-Wl,-rpath-link,$SYSROOT/opt/vc/lib"
    )

    local -r LINUX_ARM32_OPTIONS=(
        --enable-neon
    )

    local -r LINUX_ARM64_OPTIONS=(
        --enable-neon
        --pkg-config=pkg-config
    )

    local AUTOCONF_OPTIONS=()
    AUTOCONF_OPTIONS+=( "${COMMON_OPTIONS[@]}" )

    case "$TARGET" in
        rpi)
        AUTOCONF_OPTIONS+=( "${RPI_OPTIONS[@]}" )
        ;;
        linux_arm32)
        AUTOCONF_OPTIONS+=( "${LINUX_ARM32_OPTIONS[@]}" )
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
        nx_fail "Specify destination dir as an argument."
    fi

    if [[ -d "$DESTINATION_DIR" ]]
    then
        nx_fail "Destination dir already exists."
    fi
}

main()
{
    if [[ -z ${RDEP_PACKAGES_DIR:-}} ]]
    then
        nx_fail "RDEP_PACKAGES_DIR should be defined."
    fi

    if (( $# > 0 )) && [[ $1 == "--no-rdep" ]]
    then
        local -r -i NO_RDEP=1
        shift
    else
        local -r -i NO_RDEP=0
        if ! which rdep &>/dev/null
        then
            nx_fail "Rdep should be on path as \"rdep\"."
        fi
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

        nx_echo "Temp build dir retained for investigation: ${BUILD_ROOT_DIR}"
    }

    NX_EXIT_HOOKS+=( warnTempBuildDir )

    local -r SYSROOT="$BUILD_ROOT_DIR/sysroot"

    local -r JOB_COUNT=$(($(cat /proc/cpuinfo | grep "^processor" | wc -l)+1))

    nxInitToolchain

    local -r DEV_ARTIFACT="$RDEP_PACKAGES_DIR/$DEV_ARTIFACT_PLATFORM/$DEV_ARTIFACT_NAME"

    if (( $NO_RDEP == 0 ))
    then
        downloadArtifacts
    fi

    ( installSysroot )
    ( buildAlsaLib )
    ( buildOpenH264 )
    ( buildOgg )
    ( buildVorbis )
    ( buildLibVpx )
    ( buildLame )
    ( buildFfmpeg "$(nx_absolute_path "$DESTINATION_DIR")" )

    echo "Removing build dir $BUILD_ROOT_DIR"
    rm -rf "$BUILD_ROOT_DIR"
}

nx_run "$@"
