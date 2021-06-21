#!/bin/bash

set -e #< Stop on first error.

customizationName="metavms"

if [[ "$1" == "--help" || "$1" == "-h" ]]
then
    cat << \
EOF
This script runs cmake configuration stage with the necessary parameters for the given target
platform (if the target platform isn't stated eplicitly via the "TARGET_DEVICE" environment
variable it is considered to be the same that the build platform). You may pass additional cmake
configuration options via the script arguments.

Usage:
    $0 [<cmake_configure_options>]
    or
    $0 [-h|--help]

    If you need to build for the target architecture different than default for the build
    platfrom, you should set the "TARGET_DEVICE" variable accordingly. The possible values are:
    linux_x64, linux_arm64, linux_arm32, windows_x64, macos_x64, macos_arm64.
EOF

    exit 0
fi

# "readlink -f" does not work in MacOS, hence an alternative impl via "pwd -P".
baseDir=$(cd "$(dirname "$0")" && pwd -P)

if [[ -z "$TARGET_DEVICE" ]]
then
    case $OSTYPE in
        "darwin"* )
            if uname -p | grep -q arm
            then
                TARGET_DEVICE="macos_arm64"
            else
                TARGET_DEVICE="macos_x64"
            fi;;
        "msys"* ) TARGET_DEVICE="windows_x64";;
        "cygwin"* )
            TARGET_DEVICE="windows_x64"
            baseDir=$(cygpath -w "$baseDir") #< Convert cygwin's path to Windows path.
            ;;
        * ) TARGET_DEVICE="linux_x64";;
    esac
fi

# If needed, these variables can be set before running this script.
: ${buildDir=${baseDir}/../nx-open-build-${TARGET_DEVICE}}
: ${RDEP_PACKAGES_DIR=$baseDir/packages}
: ${conanDir=$baseDir/conan}
: ${srcDir=$baseDir/nx/open_candidate}

case $TARGET_DEVICE in
    "windows_x64")
        qtDir="${conanDir}/data/qt/5.15.2/_/_/package/5c53e1c6f36e23a91c9746818393c494757e5d22"
        OpensslDir="${conanDir}/data/OpenSSL-Fixed/1.1.1i/_/_/package/c86f468b3051ddb1d94e1c6b6fe74d4645707393"
        FfmpegDir="${conanDir}/data/ffmpeg/3.1.9/_/_/package/f33cd0d25fae8a874eeed73e22be3b24d878dbcf"
        fliteDir="${conanDir}/data/flite/2.2/_/_/package/3fb49604f9c2f729b85ba3115852006824e72cab"
        hidapiDir="${conanDir}/data/hidapi/0.10.1/_/_/package/3fb49604f9c2f729b85ba3115852006824e72cab"
    ;;
    "linux_x64")
        qtDir="${conanDir}/data/qt/5.15.2/_/_/package/6cd5712ab6726fc0ddb9aace96a4f927d6fbf261"
        OpensslDir="${conanDir}/data/OpenSSL-Fixed/1.1.1i/_/_/package/7c6ba434d013d96fa4eda94bb13f6f40d9ea2b98"
        FfmpegDir="${conanDir}/data/ffmpeg/3.1.9/_/_/package/d99731205b291e76d16d4663242ee3fff4e30481"
        fliteDir="${conanDir}/data/flite/2.2/_/_/package/9641b45d3074fb288997f0c8411a9a30ff177398"
        hidapiDir="${conanDir}/data/hidapi/0.10.1/_/_/package/312cfb0686778c8adc6913601d8a994200ab257c"
        toolchainDir="${conanDir}/data/gcc-toolchain/10.2/_/_/package/f24d9d4a49445fd389b06d3f22addc2784700473"
        OS_DEPS_ROOT_DIR="${conanDir}/data/os_deps_for_desktop_linux/ubuntu_xenial/_/_/package/df03044ec3e9ce2da8a0b4e7d9ae4e1aa15cb542"
    ;;
    *)
    echo "Unsupported platform"
        exit 1
        ;;
esac

if [[ "$OSTYPE" == "linux-gnu"* ]]
then
    cmake -GNinja -B${buildDir} \
        -DtargetDevice=${TARGET_DEVICE} -DqtDir=${qtDir} -DopenSslDir=${OpensslDir} \
        -DtoolchainDir=${toolchainDir} -DffmpegDir=${FfmpegDir} \
        -DosDepsRoot=${OS_DEPS_ROOT_DIR} -DfliteDir=${fliteDir} -DhidapiDir=${hidapiDir} \
        -Dcustomization=${customizationName} -DCMAKE_BUILD_TYPE=Release \
        $@ "${srcDir}"
else
    cmake -GNinja -DCMAKE_C_COMPILER="cl.exe" -DCMAKE_CXX_COMPILER="cl.exe" \
        -B${buildDir} \
        -DtargetDevice=${TARGET_DEVICE} -DqtDir=${qtDir} -DopenSslDir=${OpensslDir} \
        -DffmpegDir=${FfmpegDir} -DfliteDir=${fliteDir} -DhidapiDir=${hidapiDir} \
        -Dcustomization=${customizationName} -DCMAKE_BUILD_TYPE=Release \
        $@ "${srcDir}"
fi

echo
echo "CMake configuration succeeded; now building the project."
echo

cmake --build "$buildDir"

echo
echo "Build succeded."
