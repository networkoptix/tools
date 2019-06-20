#!/bin/bash

#-------------------------------------------------------------------------------------------------

nxPrepareSources() # PKG_SRC_DIR
{
    local -r PKG_SRC_DIR="$1"
    local -r PKG_NAME=$(basename "$PKG_SRC_DIR")
    local -r BUILD_DIR="${BUILD_ROOT_DIR}/$PKG_NAME"

    cp -af "$PKG_SRC_DIR" "$BUILD_ROOT_DIR/"

    nx_cd "$BUILD_DIR"

    if ls "$TARGET_ARTIFACT_DEV/src/patches/$PKG_NAME"-* &>/dev/null
    then
        for patch in "$TARGET_ARTIFACT_DEV/src/patches/$PKG_NAME"-*
        do
            nx_verbose patch -Np1 -i "$patch"
        done
    fi
}

#-------------------------------------------------------------------------------------------------

declare -rA ARCH_BY_TARGET=(
    [linux_arm32]=arm
    [rpi]=arm
    [linux_arm64]=aarch64
)

#-------------------------------------------------------------------------------------------------

# [in] TARGET
# [export] PATH
nxInitToolchain()
{
    local -rA GCC_ARTIFACT_GROUP_BY_TARGET=(
        [linux_arm32]="rpi"
        [linux_arm64]="linux_arm64"
        [rpi]="rpi"
    )

    local -rA GCC_ARTIFACT_BY_TARGET=(
        [linux_arm32]="gcc-4.8.3"
        [linux_arm64]="gcc-8.1"
        [rpi]="gcc-4.8.3"
    )

    local -rA GCC_PREFIX_BY_TARGET=(
        [linux_arm32]="arm-linux-gnueabihf-"
        [linux_arm64]="aarch64-linux-gnu-"
        [rpi]="arm-linux-gnueabihf-"
    )

    declare -r -g GCC_ARTIFACT_GROUP="${GCC_ARTIFACT_GROUP_BY_TARGET[$TARGET]}"
    declare -r -g GCC_ARTIFACT="${GCC_ARTIFACT_BY_TARGET[$TARGET]}"
    declare -r -g GCC_PREFIX="${GCC_PREFIX_BY_TARGET[$TARGET]}"
    declare -r -g GCC_ARTIFACT_PATH="$RDEP_PACKAGES_DIR/$GCC_ARTIFACT_GROUP/$GCC_ARTIFACT"

    export PATH="$PATH:$GCC_ARTIFACT_PATH/bin"
}

# [export] LD
# [export] AR
# [export] STRIP
# [export] RANLIB
# [export] AS
# [export] CC
# [export] CXX
nxExportToolchainMediatorVars()
{
    export \
        LD=${GCC_PREFIX}gcc \
        AR=${GCC_PREFIX}ar \
        STRIP=${GCC_PREFIX}strip \
        RANLIB=${GCC_PREFIX}ranlib \
        AS=${GCC_PREFIX}as \
        CC=${GCC_PREFIX}gcc \
        CXX=${GCC_PREFIX}c++
}

# [in] RDEP_PACKAGES_DIR
# [in] GCC_ARTIFACT 
# [in] GCC_ARTIFACT_GROUP
nxDownloadGccArtifact()
{
    rm -rf "$GCC_ARTIFACT_PATH"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$GCC_ARTIFACT_GROUP" "$GCC_ARTIFACT"
}

#-------------------------------------------------------------------------------------------------

nxMake()
{
    nx_verbose make -j "$@"
}

#-------------------------------------------------------------------------------------------------

nxConfigure()
{
    nx_verbose ./configure "$@"
}

# [in] AUTOCONF_OPTIONS (optional)
# [in] TOOLCHAIN_PREFIX (optional)
# [in] DESTDIR or SYSROOT
# [export] PKG_CONFIG_PATH
nxAutotoolsBuild()
{
    nxExportToolchainMediatorVars

    export PKG_CONFIG_PATH="$SYSROOT/usr/lib/pkgconfig"

    nxConfigure "${AUTOCONF_OPTIONS[@]}"

    nxMake

    # Install build results to DESTDIR or SYSROOT. If DESTDIR was not passed, SYSROOT will be used.
    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

#-------------------------------------------------------------------------------------------------

nxCmake()
{
    nx_verbose cmake "$@"
}

# [in] CMAKE_GEN_OPTIONS (optional)
# [in] CMAKE_BUILD_OPTIONS (optional)
# [in] DESTDIR or SYSROOT
nxCmakeBuild()
{
    nxCmake -G "Unix Makefiles" "${CMAKE_GEN_OPTIONS[@]}" .

    nxCmake --build "${CMAKE_BUILD_OPTIONS[@]}" .

    # Install build results to DESTDIR or SYSROOT. If DESTDIR was not passed, SYSROOT will be used.
    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

