#!/bin/bash

if [[ "$1" == *h* ]]; then
cat <<END
Usage: mvn.sh [flags] [extra-args]
General flags:
    c   clean up before run (e.g. hg purge --all)
    p   package (instead of compile)
    m   run makepro.py after maven
    N   do not run mvn
Target flags:
    S   build mediaserver only
    C   build desktop client only
    D   build deb packages (useful with S and C)
Build configuration flags:
    r   -Dbuild.configuration=release (instead of debug)
    u   build unit tests as well (-Dut)
    b   NX1 (-Darch=arm -Dbox=bpi)
    i   ISD (-Darch=arm -Dbox=isd)
    I   ISD (-Darch=arm -Dbox=isd_s2)
END
exit 0
fi

set -e -x
FLAGS=$1
[[ "$FLAGS" ]] && shift

[[ "$FLAGS" = *p* ]] && ACTION=package || ACTION=compile
[[ "$FLAGS" = *r* ]] && CONF=release || CONF=debug

OPTIONS="-Dbuild.configuration=$CONF $@"
[[ "$FLAGS" = *u* ]] && OPTIONS+=" -Dutb"
[[ "$FLAGS" = *b* ]] && OPTIONS+=" -Darch=arm -Dbox=bpi"
[[ "$FLAGS" = *i* ]] && OPTIONS+=" -Darch=arm -Dbox=isd"
[[ "$FLAGS" = *I* ]] && OPTIONS+=" -Darch=arm -Dbox=isd_s2"

PROJECT=
[[ "$FLAGS" = *S* ]] && PROJECT="mediaserver"
[[ "$FLAGS" = *C* ]] && PROJECT="desktop-client"
[[ "$FLAGS" = *D* ]] && PROJECT="debsetup/$PROJECT-deb"
[[ "$PROJECT" ]] && OPTIONS+=" --projects $PROJECT --also-make"

if [[ "$FLAGS" = *c* ]]; then
    hg st -i | awk '{print$2}' | grep -Ev "\.pro\.user$" | xargs rm || true
fi

[[ "$FLAGS" != *N* ]] && mvn $ACTION $OPTIONS

if [[ "$FLAGS" = *m* ]]; then
    SCRIPT_DIR=$(dirname "${BASH_SOURCE[0]}")
    $SCRIPT_DIR/makepro.py $OPTIONS
fi

