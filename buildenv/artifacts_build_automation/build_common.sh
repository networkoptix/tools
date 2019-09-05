#!/bin/bash

#-------------------------------------------------------------------------------------------------

# [in] DEV_ARTIFACT
nxPrepareSources() # PKG_SRC_DIR
{
    local -r PKG_SRC_DIR="$1"
    local -r PKG_NAME=$(basename "$PKG_SRC_DIR")
    local -r BUILD_DIR="$BUILD_ROOT_DIR/$PKG_NAME"

    cp -a "$PKG_SRC_DIR" "$BUILD_ROOT_DIR/"

    nx_cd "$BUILD_DIR"

    if ls "$DEV_ARTIFACT/src/patches/$PKG_NAME"-* &>/dev/null
    then
        for patch in "$DEV_ARTIFACT/src/patches/$PKG_NAME"-*
        do
            # Apply the patch to files in the current directory. '-p1' should be used when patch
            # is executed inside the root directory of sources.
            nx_verbose patch --forward -p1 --input="$patch"
        done
    fi
}

#-------------------------------------------------------------------------------------------------

declare -rA ARCH_BY_TARGET=(
    [linux_x64]=x86_64
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
        [linux_x64]="linux_x64"
        [linux_arm32]="rpi"
        [linux_arm64]="linux_arm64"
        [rpi]="rpi"
    )

    local -rA GCC_ARTIFACT_BY_TARGET=(
        [linux_x64]="gcc-8.1"
        [linux_arm32]="gcc-4.8.3"
        [linux_arm64]="gcc-8.1"
        [rpi]="gcc-4.8.3"
    )

    local -rA GCC_PREFIX_BY_TARGET=(
        [linux_x64]="x86_64-pc-linux-gnu-"
        [linux_arm32]="arm-linux-gnueabihf-"
        [linux_arm64]="aarch64-unknown-linux-gnu-"
        [rpi]="arm-linux-gnueabihf-"
    )

    declare -r -g GCC_ARTIFACT_GROUP="${GCC_ARTIFACT_GROUP_BY_TARGET[$TARGET]}"
    declare -r -g GCC_ARTIFACT="${GCC_ARTIFACT_BY_TARGET[$TARGET]}"
    declare -r -g GCC_PREFIX="${GCC_PREFIX_BY_TARGET[$TARGET]}"
    declare -r -g GCC_ARTIFACT_PATH="$RDEP_PACKAGES_DIR/$GCC_ARTIFACT_GROUP/$GCC_ARTIFACT"

    export PATH="$GCC_ARTIFACT_PATH/bin:$PATH"
}

nxCheckVarIsSet() #< VAR_NAME
{
    local -r VAR_NAME="$1"; shift

    eval "[[ \${$VAR_NAME+x} ]]"
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
    nxCheckVarIsSet LD || LD=${GCC_PREFIX}gcc
    nxCheckVarIsSet AR || AR=${GCC_PREFIX}ar
    nxCheckVarIsSet STRIP || STRIP=${GCC_PREFIX}strip
    nxCheckVarIsSet RANLIB || RANLIB=${GCC_PREFIX}ranlib
    nxCheckVarIsSet AS || AS=${GCC_PREFIX}as
    nxCheckVarIsSet CC || CC=${GCC_PREFIX}gcc
    nxCheckVarIsSet CXX || CXX=${GCC_PREFIX}c++

    export LD AR STRIP RANLIB AS CC CXX
}

# [in] RDEP_PACKAGES_DIR
# [in] GCC_ARTIFACT 
# [in] GCC_ARTIFACT_GROUP
nxDownloadGccArtifact()
{
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
    echo "./configure $@" >.configure.sh
    chmod +x .configure.sh
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

    export >.env

    nxConfigure "${AUTOCONF_OPTIONS[@]}"

    nxMake

    # Install build results to DESTDIR or SYSROOT. If DESTDIR was not passed, SYSROOT will be used.
    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

#-------------------------------------------------------------------------------------------------

# [in] CMAKE_GEN_OPTIONS (optional)
# [in] DESTDIR or SYSROOT
nxCmakeBuild()
{
    export >.env

    echo "cmake -G \"Unix Makefiles\" ${CMAKE_GEN_OPTIONS:+\"${CMAKE_GEN_OPTIONS[@]}\"} ." >.cmake_gen.sh
    chmod +x .cmake_gen.sh
    nx_verbose cmake -G "Unix Makefiles" "${CMAKE_GEN_OPTIONS:+${CMAKE_GEN_OPTIONS[@]}}" .

    echo "cmake --build ." >.cmake_build.sh
    chmod +x .cmake_build.sh
    nx_verbose cmake --build .

    # Install build results to DESTDIR or SYSROOT. If DESTDIR was not passed, SYSROOT will be used.
    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

