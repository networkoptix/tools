#!/bin/bash

osDepsLibDir="./conan/data/os_deps_for_desktop_linux/ubuntu_xenial/_/_/package/df03044ec3e9ce2da8a0b4e7d9ae4e1aa15cb542/usr/lib/x86_64-linux-gnu"

export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:./conan/data/hidapi/0.10.1/_/_/package/312cfb0686778c8adc6913601d8a994200ab257c/lib"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:./packages/linux_x64/intel-media-sdk-19.4.0/lib"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:./conan/data/ffmpeg/3.1.9/_/_/package/d99731205b291e76d16d4663242ee3fff4e30481/lib"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:./packages/linux_x64/libva-2.6/lib"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$osDepsLibDir/pulseaudio"

LD_PRELOAD="$osDepsLibDir/libopenal.so.1" ../vms_4.3.0_R2_OPEN_linux_x64-build/bin/metavms_client
