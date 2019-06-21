#!/bin/bash

source "../../util/utils.sh"

set -e #< Stop on error.
set -u #< Forbid undefined variables.

source "build_common.sh"

declare -r SUPPORTED_TARGETS=( linux_arm32 linux_arm64 )
declare -r OPENSSL_VERSION="1.0.2q"
declare -r TARGET_ARTIFACT_DEV_ARTIFACT_TARGET="linux"
declare -r TARGET_ARTIFACT_DEV_ARTIFACT="openssl-dev-${OPENSSL_VERSION}"

help_callback()
{
    cat \
<<EOF
This script should be used to build openssl artifact.
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
    local -r TARGET_ARTIFACT_DEV_CHECKSUM="b00501abc9119701a5396965a1a3a5be *files.md5"

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
# [in] TARGET_ARTIFACT_DEV 
buildOpenssl() # ABSOLUTE_DESTINATION_DIR
{
    nx_echo "Building openssl..."

    local -r ABSOLUTE_DESTINATION_DIR="$1"

    nxPrepareSources "$TARGET_ARTIFACT_DEV/src/openssl-$OPENSSL_VERSION"

    nxExportToolchainMediatorVars "${GCC_PREFIX}"

    local -rA TARGET_OPTION_BY_TARGET=(
        [linux_arm32]=linux-armv4
        [linux_arm64]=linux-aarch64
    )

    ./Configure --prefix=/ shared "${TARGET_OPTION_BY_TARGET[$TARGET]}"

    nxMake PREFIX=/usr
    nxMake PREFIX=/usr INSTALL_PREFIX="$ABSOLUTE_DESTINATION_DIR" install

    # There is no way to disable documentation compilation, so just remove it after the build.
    rm -rf "$ABSOLUTE_DESTINATION_DIR/ssl/man"

    # There is no way to prevent static libraries linking, so just remove static libraries after
    # the build.
    rm -rf "$ABSOLUTE_DESTINATION_DIR/lib/"*.a
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

    local -r BUILD_ROOT_DIR=$(mktemp -d -p "${TMPDIR:-/tmp}" --suffix=-openssl_build)

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

    ( buildOpenssl "$(nx_absolute_path "$DESTINATION_DIR")" )

    rm -rf "$BUILD_ROOT_DIR"
}

nx_run "$@"

