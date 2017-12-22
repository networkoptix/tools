#!/bin/bash

PARTS="Clouds DesktopClient MediaServer MobileClient TestCamera Tests TrayTool"
if [[ "$1" == *-h* ]]; then
cat <<END
Usage: [OPTION=value] $0 [cmake-options]
Options:
    B   = Taret to build after configure, default is none
    BD  = Build directory, default is ./build
    C   = 1 for clean up before run (e.g. rm build)
    R   = 1 for release build (used only with B)
    RD  = RDep sync option, default is OFF
    UP  = 1 fot mercurial pull & update
    W   = Flags to include only some parts into build.
Examples:
    DB=../nx_vms-3.0 $0 -Dcustomization=hanwha
    C=1 UP=1 W=MC B=mediaserver R=1 $0
Part flags:
END
for PART in $PARTS; do echo "    ${PART:0:1}   = $PART"; done
exit 0
fi

set -e -x

OPTIONS="-DrdepSync=${RD:-OFF}"
if cat /etc/os-release 2>/dev/null | grep -q Ubuntu; then
    OPTIONS+=" -GNinja"
else
    OPTIONS+=" -Ax64"
fi

BUILD_DIR=${BD:-"./build"}
[[ "$C" ]] && rm -rf "$BUILD_DIR"
[[ "$UP" ]] && hg pull && hg update
[[ "$R" ]] && OPTIONS+="--config Release"

PARTS="Clouds DesktopClient MediaServer MobileClient TestCamera Tests TrayTool"
if [ $W ]; then
    for WITH in $PARTS; do
        if [[ $W == *${WITH:0:1}* ]]; then
            OPTIONS+=" -Dwith$WITH=ON"
        else
            OPTIONS+=" -Dwith$WITH=OFF"
        fi
    done
fi

SOURCE_DIR="$PWD"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"
cmake $SOURCE_DIR $OPTIONS "$@"

if [ "$B" ]; then
    OPTIONS="--build ."
    [ "$R" ] && OPTIONS+=" --config Release"
    cmake $OPTIONS --target "$B" "$@"
fi
