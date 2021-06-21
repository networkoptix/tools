#!/bin/bash

set -e #< Stop on first error.

if [[ "$1" == "--help" || "$1" == "-h" ]]
then
    cat \
<<EOF
This script runs cmake configuration and build stages with the necessary parameters for Linux.
You may pass additional cmake configuration options via the script arguments.

Usage:
    $0 [<cmake_configure_options>]
    or
    $0 [-h|--help]
EOF

    exit 0
fi

customization="metavms"
cloudHost="meta.nxvms.com"

baseDir=$(cd "$(dirname "$0")" && pwd -P)

# If needed, these variables can be set before running this script.
: ${buildDir=${baseDir}/../vms_4.3.0_R2_OPEN_linux_x64-build}
: ${conanDir=$baseDir/conan}
: ${srcDir=$baseDir/nx/open_candidate}
: ${RDEP_PACKAGES_DIR=$baseDir/packages}
export RDEP_PACKAGES_DIR #< This variable is used by cmake scripts to locate some artifacts.

# These variables define the location of certain artifacts.
qtDir="${conanDir}/data/qt/5.15.2/_/_/package/6cd5712ab6726fc0ddb9aace96a4f927d6fbf261"
openSslDir="${conanDir}/data/OpenSSL-Fixed/1.1.1i/_/_/package/7c6ba434d013d96fa4eda94bb13f6f40d9ea2b98"
ffmpegDir="${conanDir}/data/ffmpeg/3.1.9/_/_/package/d99731205b291e76d16d4663242ee3fff4e30481"
fliteDir="${conanDir}/data/flite/2.2/_/_/package/9641b45d3074fb288997f0c8411a9a30ff177398"
hidapiDir="${conanDir}/data/hidapi/0.10.1/_/_/package/312cfb0686778c8adc6913601d8a994200ab257c"
toolchainDir="${conanDir}/data/gcc-toolchain/10.2/_/_/package/f24d9d4a49445fd389b06d3f22addc2784700473"
osDepsRoot="${conanDir}/data/os_deps_for_desktop_linux/ubuntu_xenial/_/_/package/df03044ec3e9ce2da8a0b4e7d9ae4e1aa15cb542"

cmake \
    -B "$buildDir" \
    -G Ninja \
    -DtargetDevice=linux_x64 \
    -DqtDir="$qtDir" \
    -DopenSslDir="$openSslDir" \
    -DtoolchainDir="$toolchainDir" \
    -DffmpegDir="$ffmpegDir" \
    -DosDepsRoot="$osDepsRoot" \
    -DfliteDir="$fliteDir" \
    -DhidapiDir="$hidapiDir" \
    -Dcustomization="$customization" \
    -DcloudHost="$cloudHost" \
    -DCMAKE_BUILD_TYPE=Release \
    "$@" \
    "$srcDir"

echo
echo "CMake configuration succeeded; now building the project."
echo

cmake --build "$buildDir"

echo
echo "Build succeded."
