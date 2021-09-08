#!/bin/bash

allChars=""
for code in $(seq 127 255)
do
    char=$(printf "\\$(printf %o $code)")
    if [[ ! -z $allChars ]]
    then
        allChars+="\\|"
    fi
    allChars+="$char"
done

grep \
    --include "*.c" --include "*.cpp" --include "*.h" --include "*.hpp" \
    --exclude-dir=.git --exclude-dir=.vs --exclude-dir=.vscode --exclude-dir=_ReSharper.Caches \
    --color=auto -r \
    "$@" \
    "$allChars"
