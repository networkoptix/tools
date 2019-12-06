#!/bin/bash

# Packs specified binary with all libraries that are located under non-standard paths.
# Usage:
# pack_bin /path/to/binary


BINARY=$1
PREFIX=$2

if [ ! -f $BINARY ]; then
    echo "File $BINARY not found"
    exit 1
fi

echo -n "Packing $BINARY with dependencies"
if [ ! -z "$PREFIX" ]; then
    echo " with prefix $PREFIX"
else
    echo ""
fi

LIBS=(`ldd $BINARY  | grep "=>" | sed 's/.*=> \(.*\) (.*/\1/g' | grep -v "^/lib/" | grep -v "^/usr/lib/"`)

LIBDIR=./dist/$PREFIX/lib/

mkdir -p $LIBDIR
mkdir -p ./dist/$PREFIX/bin/
for i in "${LIBS[@]}"
do
    echo "  Packing $i"
    cp $i $LIBDIR
done

echo "  Packing $BINARY"
cp $BINARY ./dist/$PREFIX/bin/

pushd ./dist/
ARCHIVE_NAME=$(basename $BINARY).tar.gz
tar czf $ARCHIVE_NAME ./$PREFIX/bin ./$PREFIX/lib
popd
mv ./dist/$ARCHIVE_NAME .
rm -rf ./dist

echo "Saved to $ARCHIVE_NAME"
