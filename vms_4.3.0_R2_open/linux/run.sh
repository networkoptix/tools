#!/bin/bash

baseDir=$(cd "$(dirname "$0")" && pwd -P)
buildDir="$baseDir/../vms_4.3.0_R2_OPEN_linux_x64-build"

toolchainLibsDir="$baseDir/conan/data/gcc-toolchain/10.2/_/_/package/f24d9d4a49445fd389b06d3f22addc2784700473/x86_64-linux-gnu/sysroot/lib"
sysrootLibsDir="$baseDir/conan/data/os_deps_for_desktop_linux/ubuntu_xenial/_/_/package/df03044ec3e9ce2da8a0b4e7d9ae4e1aa15cb542/lib/x86_64-linux-gnu"
sysrootUsrLibsDir="$baseDir/conan/data/os_deps_for_desktop_linux/ubuntu_xenial/_/_/package/df03044ec3e9ce2da8a0b4e7d9ae4e1aa15cb542/usr/lib/x86_64-linux-gnu"
ffmpegLibsDir="$baseDir/conan/data/ffmpeg/3.1.9/_/_/package/d99731205b291e76d16d4663242ee3fff4e30481/lib"
openSslLibsDir="$baseDir/conan/data/OpenSSL-Fixed/1.1.1i/_/_/package/7c6ba434d013d96fa4eda94bb13f6f40d9ea2b98/lib"
hidapiLibsDir="$baseDir/conan/data/hidapi/0.10.1/_/_/package/312cfb0686778c8adc6913601d8a994200ab257c/lib"
libvaLibsDir="$baseDir/packages/linux_x64/libva-2.6/lib"
intelmediasdkLibsDir="$baseDir/packages/linux_x64/intel-media-sdk-19.4.0/lib"
qtDir="$baseDir/conan/data/qt/5.15.2/_/_/package/6cd5712ab6726fc0ddb9aace96a4f927d6fbf261"

copyLibsIfNeeded()
{
    # Copy system libraries.

    mkdir -p "$buildDir/lib/stdcpp"
    mkdir -p "$buildDir/lib/gstreamer-0.10"

    cp -u "$toolchainLibsDir/libstdc++.so.6.0.28" "$buildDir/lib/stdcpp/"
    cp -u "$toolchainLibsDir/libatomic.so.1.2.0" "$buildDir/lib/stdcpp/"
    cp -u "$toolchainLibsDir/libgcc_s.so.1" "$buildDir/lib/stdcpp/"
    cp -u "$toolchainLibsDir/libmvec-2.23.so" "$buildDir/lib/stdcpp/"
    cp -u "$sysrootLibsDir/libpng12.so.0.54.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libXss.so.1.0.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libxcb-xinerama.so.0.0.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libopenal.so.1.16.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstapp-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstbase-1.0.so.0.800.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstreamer-1.0.so.0.800.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstpbutils-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstaudio-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgsttag-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstvideo-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstfft-1.0.so.0.803.0" "$buildDir/lib/"
    cp -u "$sysrootUsrLibsDir/libgstreamer-0.10.so.0.30.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$sysrootUsrLibsDir/libgstapp-0.10.so.0.25.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$sysrootUsrLibsDir/libgstbase-0.10.so.0.30.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$sysrootUsrLibsDir/libgstinterfaces-0.10.so.0.25.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$sysrootUsrLibsDir/libgstpbutils-0.10.so.0.25.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$sysrootUsrLibsDir/libgstvideo-0.10.so.0.25.0" "$buildDir/lib/gstreamer-0.10/"
    cp -u "$ffmpegLibsDir/libavcodec.so.57.48.101" "$buildDir/lib/"
    cp -u "$ffmpegLibsDir/libavfilter.so.6.47.100" "$buildDir/lib/"
    cp -u "$ffmpegLibsDir/libavformat.so.57.41.100" "$buildDir/lib/"
    cp -u "$ffmpegLibsDir/libavutil.so.55.28.100" "$buildDir/lib/"
    cp -u "$ffmpegLibsDir/libswscale.so.4.1.100" "$buildDir/lib/"
    cp -u "$ffmpegLibsDir/libswresample.so.2.1.100" "$buildDir/lib/"
    cp -u "$openSslLibsDir/libcrypto.so.1.1" "$buildDir/lib/"
    cp -u "$openSslLibsDir/libssl.so.1.1" "$buildDir/lib/"
    cp -u "$hidapiLibsDir/libhidapi-hidraw.so.0.0.0" "$buildDir/lib/"
    cp -u "$libvaLibsDir/libva.so.2.600.0" "$buildDir/lib/"
    cp -u "$libvaLibsDir/libva-x11.so.2.600.0" "$buildDir/lib/"
    cp -u "$intelmediasdkLibsDir/libmfxhw64.so.1.31" "$buildDir/lib/"
    cp -u "$intelmediasdkLibsDir/libmfx.so.1.31" "$buildDir/lib/"

    pushd "$buildDir/lib" >/dev/null
    {
        ln -s libavcodec.so.57.48.101 libavcodec.so.57
        ln -s libavfilter.so.6.47.100 libavfilter.so.6
        ln -s libavformat.so.57.41.100 libavformat.so.57
        ln -s libavutil.so.55.28.100 libavutil.so.55
        ln -s libswscale.so.4.1.100 libswscale.so.4
        ln -s libswresample.so.2.1.100 libswresample.so.2
        ln -s libhidapi-hidraw.so.0.0.0 libhidapi-hidraw.so.0
        ln -s libstdc++.so.6.0.28 stdcpp/libstdc++.so.6
        ln -s libatomic.so.1.2.0 stdcpp/libatomic.so.1
        ln -s libmvec-2.23.so stdcpp/libmvec.so.1
        ln -s libXss.so.1.0.0 libXss.so.1
        ln -s libxcb-xinerama.so.0.0.0 libxcb-xinerama.so.0
        ln -s libopenal.so.1.16.0 libopenal.so.1
        ln -s libpng12.so.0.54.0 libpng12.so.0
        ln -s libgstapp-1.0.so.0.803.0 libgstapp-1.0.so.0
        ln -s libgstbase-1.0.so.0.800.0 libgstbase-1.0.so.0
        ln -s libgstreamer-1.0.so.0.800.0 libgstreamer-1.0.so.0
        ln -s libgstpbutils-1.0.so.0.803.0 libgstpbutils-1.0.so.0
        ln -s libgstaudio-1.0.so.0.803.0 libgstaudio-1.0.so.0
        ln -s libgsttag-1.0.so.0.803.0 libgsttag-1.0.so.0
        ln -s libgstvideo-1.0.so.0.803.0 libgstvideo-1.0.so.0
        ln -s libgstfft-1.0.so.0.803.0 libgstfft-1.0.so.0
        ln -s libgstreamer-0.10.so.0.30.0 gstreamer-0.10/libgstreamer-0.10.so.0
        ln -s libgstapp-0.10.so.0.25.0 gstreamer-0.10/libgstapp-0.10.so.0
        ln -s libgstbase-0.10.so.0.30.0 gstreamer-0.10/libgstbase-0.10.so.0
        ln -s libgstinterfaces-0.10.so.0.25.0 gstreamer-0.10/libgstinterfaces-0.10.so.0
        ln -s libgstpbutils-0.10.so.0.25.0 gstreamer-0.10/libgstpbutils-0.10.so.0
        ln -s libgstvideo-0.10.so.0.25.0 gstreamer-0.10/libgstvideo-0.10.so.0
        ln -s libva.so.2.600.0 libva.so.2
        ln -s libva-x11.so.2.600.0 libva-x11.so.2
        ln -s libmfxhw64.so.1.31 libmfxhw64.so.1
        ln -s libmfx.so.1.31 libmfx.so.1
    } 2>/dev/null
    popd >/dev/null

    # Copy qt directories and libraries.

    for dir in plugins libexec resources qml
    do
        cp -r -u "$qtDir/$dir" "$buildDir/"
    done
    mkdir -p "$buildDir/translations"
    cp -r -u "$qtDir/translations/qtwebengine_locales" "$buildDir/translations/"

    cp -u "$qtDir"/lib/libQt5*.so* "$buildDir/lib/"
}

copyLibsIfNeeded
export LD_LIBRARY_PATH="$buildDir/lib/stdcpp:$LD_LIBRARY_PATH"
"$buildDir/bin/metavms_client"
