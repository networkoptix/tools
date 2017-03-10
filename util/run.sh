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
    T   use 1 for time  measure
    Q   specific qt version in library path's
Example:
    run.sh mediaserver -e   # run mediaserver
    R=1 V="--tool=exp-dhat" run.sh client.bin   # run release client under valgrind dhat
    A=bpi C=./core run.sh mediaserver   # open mediaserver core for bpi
    VT=mem O=/tmp/network.vg nx_network_ut --ll=DEBUG2   # run network tests with valgrind
END
exit 0
fi

set -e
[[ $NOX ]] || set -x

EXTRA=debug/
[ "$R" ] && EXTRA=release/
[ "$L" ] && ulimit -c unlimited

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
        GDB=/Applications/Xcode.app/Contents/Developer/usr/bin/lldb; GDB_ARGS=--; OS_GREP=macosx

        # /usr/bin/lldb is protected against LD variables
        [[ "$C$D" ]] && sudo /usr/sbin/DevToolsSecurity --enable
    else
        GDB=gdb; GDB_ARGS=--args; OS_GREP=linux
    fi
fi

# Setup required PATH variables from rdep packages and
export PATH="$PWD/build_environment/target/bin/$EXTRA:$PATH"
set +x
BUILD_LIB_DIRS="$PWD/build_environment/target$ARCH/lib/$EXTRA"
RDEP_LIB_DIRS=$(find "$PWD/../buildenv/packages/" -name lib -o -name platforms \
        | sort -r | grep $OS_GREP-$ARCH_GREP | awk "/qt-$Q/ || !/qt-/" \
        | while read L; do echo -n ":${L}"; done)

[[ $NOX ]] && set -x
if [ $(uname) == Darwin ]; then
    export DYLD_LIBRARY_PATH="$BUILD_LIB_DIRS:$DYLD_LIBRARY_PATH:$RDEP_LIB_DIRS"
    export DYLD_FRAMEWORK_PATH="$DYLD_FRAMEWORK_PATH:$RDEP_LIB_DIRS"
else
    export LD_LIBRARY_PATH="$BUILD_LIB_DIRS:$LD_LIBRARY_PATH:$RDEP_LIB_DIRS"
fi

# Update $V (valgrind options) in case of $VT (some tool is selected)
if [ "$VT" ]; then
    OLD_V="$V"
    VS=${VS:-$(readlink -f $(dirname "${BASH_SOURCE[0]}")/..)/valgrind/memcheck-ms.supp}
    case "$VT" in
        *leak*) V="--leak-check=yes --show-leak-kinds=definite --undef-value-errors=no --suppressions=$VS" ;;
        *rw*) V="--leak-check=no --undef-value-errors=no" ;;
        *dhat*) V="--tool=exp-dhat --show-top-n=100 --sort-by=max-bytes-live" ;;
        *mass*) V="--tool=massif" ;;
        *call*) V="--tool=callgrind --callgrind-out-file=$1-$(time +%s).cg" ;;
        *) echo "Unsupported tool: $VT" >&2; exit 1 ;;
    esac
    V+=" --num-callers=25 $OLD_V"
fi

if [ "$C" ]; then $GDB $@ $C
elif [ "$D" ]; then $GDB $GDB_ARGS $@
elif [ "$DS" ]; then gdbserver :$DS $@
elif [ "$ST" ]; then strace $@ $REDIRECT
elif [ "$V" ]; then valgrind $V $@ $REDIRECT
elif [ "$T" ]; then time $@ $REDIRECT
else $@; fi
