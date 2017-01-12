#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs VMS binaries in console
Usage: [OPTION=VALUE ...] run.sh [--help] <binary-name> [<binary-args>]
Options:
    R   relese, use 1 for release
    A   arch, e.g. bpi
    N   use 1 to skip rdep LD_LIBRARY_PATH (prior 2.6)
    L   use 1 for ulimit -c unlimited
    C   path to core dump for gdb
    D   use 1 for gdb run
    ST  use 1 for strace run
    V   valgrind args, empty means no valgrind
Example:
    run.sh mediaserver -e   # run mediaserver
    R=1 V="--tool=exp-dhat" run.sh client.bin   # run release client under valgrind dhat
    A=bpi C=./core run.sh mediaserver   # open mediaserver core for bpi
END
exit 0
fi

set -x -e

if [ "$R" ]
then
    EXTRA=release/
else
    EXTRA=debug/
fi

if [ "$A" ]
then
    ARCH=-$A
    ARCH_GREP=$A
    if [ "$A" == bpi ]
    then
        KIT=/usr/local/raspberrypi-tools/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian
        if [ $(uname) == Darwin ]
        then
            DYLD_LIBRARY_PATH=$KIT/lib
        else
            LD_LIBRARY_PATH=$KIT/lib
        fi
        GDB=$KIT/bin/arm-linux-gnueabihf-gdb
    else
        echo Unsupported box: $A
        exit 1
    fi
else
    ARCH=
    ARCH_GREP=x64
    if [ $(uname) == Darwin ]
    then
        # /usr/bin/lldb is protected against LD variables
        GDB=/Applications/Xcode.app/Contents/Developer/usr/bin/lldb
        GDB_ARGS=--
        OS_GREP=macosx
        if [[ $C$D ]]; 
        then
            sudo /usr/sbin/DevToolsSecurity --enable
        fi
    else
        GDB=gdb
        GDB_ARGS=--args
        OS_GREP=linux
    fi
fi

function find_libs() {
    set +x
    find "$PWD/../buildenv/packages/" -name lib -o -name platforms |\
        sort -r | grep $OS_GREP-$ARCH_GREP |\
        while read L; do echo -n ":${L}"; done
    set -x
}

export PATH="$PWD/build_environment/target/bin/$EXTRA:$PATH"
if [ $(uname) == Darwin ]
then
    export DYLD_LIBRARY_PATH="$PWD/build_environment/target$ARCH/lib/$EXTRA:$DYLD_LIBRARY_PATH$(find_libs)"
    export DYLD_FRAMEWORK_PATH="$DYLD_FRAMEWORK_PATH$(find_libs)"
else
    export LD_LIBRARY_PATH="$PWD/build_environment/target$ARCH/lib/$EXTRA:$LD_LIBRARY_PATH$(find_libs)"
fi


if [ "$L" ]
then
    ulimit -c unlimited
fi

if [ "$C" ]
then
    $GDB $@ $C
elif [ "$D" ]
then
    $GDB $GDB_ARGS $@
elif [ "$DS" ]
then
    gdbserver :$DS $@
elif [ "$ST" ]
then
    strace $@
elif [ "$V" ]
then
    valgrind $V $@
else
    $@
fi
