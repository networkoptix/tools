#!/bin/bash

# [in] TARGET
initToolchain()
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

setToolchainMediatorVars()
{
    export \
        LD=${GCC_PREFIX}gcc \
        AR=${GCC_PREFIX}ar \
        STRIP=${GCC_PREFIX}strip \
        AS=${GCC_PREFIX}as \
        CC=${GCC_PREFIX}gcc \
        CXX=${GCC_PREFIX}c++
}

# [in] RDEP_PACKAGES_DIR
# [in] GCC_ARTIFACT 
# [in] GCC_ARTIFACT_GROUP
downloadGccArtifact()
{
    rm -rf "$GCC_ARTIFACT_PATH"
    nx_verbose rdep --root "$RDEP_PACKAGES_DIR" -t "$GCC_ARTIFACT_GROUP" "$GCC_ARTIFACT"
}

