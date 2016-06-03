#!/bin/bash

if [[ "$1" == *h* ]]; then
cat <<END
Usage: mvn.sh [flags] [extra-args]
Flags:
    p   package (instead of compile)
    r   -Dbuild.configuration=release (instead of debug)
    u   build unit tests as well (-Dut)
    b   NX1 (-Darch=arm -Dbox=bpi)
    c   clean up before run (e.g. hg purge --all)
END
exit 0
fi

set -e -x

[[ "$1" = *p* ]] && ACTION=package || ACTION=compile
[[ "$1" = *r* ]] && CONF=release || CONF=debug

OPTIONS=
[[ "$1" = *u* ]] && OPTIONS+=" -Dut"
[[ "$1" = *b* ]] && OPTIONS+=" -Darch=arm -Dbox=bpi"

if [[ "$1" = *c* ]]; then
    hg st -i | awk '{print$2}' | grep -Ev "\.pro\.user$" | xargs rm || true
fi

shift
mvn $ACTION -Dbuild.configuration=$CONF $OPTIONS $@

SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
$SCRIPT_DIR/makepro.py $OPTIONS
