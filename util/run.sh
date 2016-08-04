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
        LD_LIBRARY_PATH=$KIT/lib
        GDB=$KIT/bin/arm-linux-gnueabihf-gdb
    else
        echo Unsupported box: $A
        exit 1
    fi
else
    ARCH=
    ARCH_GREP=x64
    GDB=gdb
fi

export PATH="$PWD/build_environment/target/bin/$EXTRA:$PATH"
export LD_LIBRARY_PATH="$PWD/build_environment/target$ARCH/lib/$EXTRA:$LD_LIBRARY_PATH$(
    find "$PWD/../buildenv/packages/" -name lib -o -name platforms | sort -r |\
    grep linux-$ARCH_GREP | while read L; do echo -n ":${L}"; done)"

if [ "$L" ]
then
    ulimit -c unlimited
fi

if [ "$C" ]
then
    $GDB $@ $C
elif [ "$D" ]
then
    $GDB --args $@
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
