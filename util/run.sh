#!/bin/bash

if [[ "$1" == *help ]] || [[ "$1" == -h ]]
then
cat <<END
Runs VMS binaries in console
Usage: [OPTION=VALUE ...] run.sh [--help] <binary-name> [<binary-args>]
Options:
    R   relese, use 1 for release
    A   arch, e.g. bpi
    L   use 1 for ulimit -c unlimited
    C   path to core dump for gdb to open
    D   use 1 for gdb run
    DS  use 1 for gdbserver run
    ST  use 1 for strace run
    V   valgrind args, empty means no valgrind
    VS  valgrind suppressions file (default in devtools/valgrind)
    VT  valgrind tool (modifies V), supported: leak, rw, dhat, mass, call
    T   use 1 for time measure
    Q   specific qt version in library path's
Notes:
    Windows support (cygwin, git-bash, etc) is only partial, supported options: R, Q.
Example:
    run.sh mediaserver -e   # run mediaserver
    R=1 V="--tool=exp-dhat" run.sh client.bin   # run release client under valgrind dhat
    A=bpi C=./core run.sh mediaserver   # open mediaserver core for bpi
    VT=leak O=/tmp/network.vg nx_network_ut --ll=DEBUG2   # run network tests with valgrind
END
exit 0
fi

if [ $WINDIR ]; then
    DEFAULT_DEVELOP=/c/develop
else
    DEFAULT_DEVELOP=$HOME/develop
fi

set -e
[[ $NOX ]] || set -x

EXTRA=debug
[ "$R" ] && EXTRA=release

if [ $WINDIR ]; then
    DIR=$(dirname $(find . -name $1.exe | grep -i $EXTRA | head -1))
    PATH=$DEFAULT_DEVELOP/buildenv/packages/windows-x64/qt-${Q:-5.6.1-1}/bin
    $DIR/$@
    exit 0
fi

[ "$L" ] && ulimit -c unlimited
[ "$VT" ] && V="$($(readlink -f $(dirname "${BASH_SOURCE[0]}")/..)/valgrind/args.sh $VT $1) $V"

if [ "$A" ]; then
    ARCH=-$A; ARCH_GREP=$A
    if [ "$A" == bpi ]; then
        KIT=/usr/local/raspberrypi-tools/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian
        LD_LIBRARY_PATH=$KIT/lib
        GDB=$KIT/bin/arm-linux-gnueabihf-gdb
    else
        echo Unsupported box: $A 1>&2; exit 1
    fi
else
    ARCH=; ARCH_GREP=x64
    if [ $(uname) == Darwin ]; then
        ulimit -n 10000
        GDB=/Applications/Xcode.app/Contents/Developer/usr/bin/lldb; GDB_ARGS=--; OS_GREP=macosx

        # /usr/bin/lldb is protected against LD variables
        [[ "$C$D" ]] && sudo /usr/sbin/DevToolsSecurity --enable
    else
        GDB=gdb; GDB_ARGS=--args; OS_GREP=linux
    fi
fi

# Setup required PATH variables from rdep packages and
export PATH="$PWD/build-$EXTRA/bin:$PWD/build/bin:$PWD/build_environment/target/bin/$EXTRA:$PATH"
set +x
BUILD_LIB_DIRS="$PWD/build_environment/target$ARCH/lib/$EXTRA"
RDEP_LIB_DIRS=$(find "$PWD/../buildenv/packages/" -name lib -o -name platforms \
        | sort -r | grep $OS_GREP-$ARCH_GREP | awk "/qt-$Q/ || !/qt-/" \
        | while read L; do echo -n ":${L}"; done)

[[ $NOX ]] || set -x
if [ $(uname) == Darwin ]; then
    export DYLD_LIBRARY_PATH="$BUILD_LIB_DIRS:$DYLD_LIBRARY_PATH:$RDEP_LIB_DIRS"
    export DYLD_FRAMEWORK_PATH="$DYLD_FRAMEWORK_PATH:$RDEP_LIB_DIRS"
else
    export LD_LIBRARY_PATH="$BUILD_LIB_DIRS:$LD_LIBRARY_PATH:$RDEP_LIB_DIRS"
fi

if [ "$C" ]; then $GDB $@ $C
elif [ "$D" ]; then $GDB $GDB_ARGS $@
elif [ "$DS" ]; then gdbserver :$DS $@
elif [ "$ST" ]; then strace $@
elif [ "$V" ]; then valgrind $V $@
elif [ "$T" ]; then time $@
else $@; fi
