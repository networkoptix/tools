#!/bin/bash
set -e

TOOL=$1
OUT=${2:-out}
SUP=${3:-$(readlink -f $(dirname "${BASH_SOURCE[0]}")/memcheck-ms.supp)}

echo_help() {
cat >&2 <<END
Usage: args.sh [TOOL]
Tools:
    leak    Memory leak checking for possible and defenite loses [IMPORTANT]
    rw      Uninitialized values verification [RECOMENDED]
    dhat    Memory usage profiler (allocations and access) [IMPORTANT]
    mass    Memory consumption profiler over time [useful in some cases]
    call    Processor time spending analysis [useful in some cases]
END
}

SUP="--suppressions=$SUP"
case "$TOOL" in
    *help*) echo_help >&2; exit 1 ;;
    *leak*) OPT="--leak-check=yes --show-leak-kinds=definite,possible --undef-value-errors=no $SUP" ;;
    *rw*) OPT="--leak-check=no --undef-value-errors=yes $SUP" ;;
    *dhat*) OPT="--tool=exp-dhat --show-top-n=100 --sort-by=max-bytes-live" ;;
    *mass*) OPT="--tool=massif --massif-out-file=$OUT.massif" ;;
    *call*) OPT="--tool=callgrind --callgrind-out-file=$OUT.callgrind" ;;
    *) echo Error: unsupported tool: $TOOL >&2; echo_help >&2; exit 1 ;;
esac

echo $OPT --num-callers=25
