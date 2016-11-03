#!/bin/bash
MAIN_LIST=.main-list
BAK_LIST=.bak-list
function usage() {
	echo "Usage:"
	echo "\t$0 MAIN-STORAGE-PATH BACKUP-STORAGE-PATH"
	exit 1
}

if [ -z "$1" ]; then
	echo "The main storage path isn't specified"
	usage
fi

if [ -z "$2" ]; then
	echo "The backup storage path isn't specified"
	usage
fi

MAIN="$1"
BAK="$2"

find "$MAIN" -name '*.mkv' -printf '%P %s\n' > "$MAIN_LIST"
find "$BAK" -name '*.mkv' -printf '%P %s\n' > "$BAK_LIST"
if diff -q "$MAIN_LIST" "$BAK_LIST" > /dev/null; then
	echo OK
	RC=0
else
	echo DIFFEENT
	RC=1
fi
rm "$MAIN_LIST" "$BAK_LIST"
exit $RC
