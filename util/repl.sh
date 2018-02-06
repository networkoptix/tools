#!/bin/bash

BACKUP_SUFFIX=".repl.BAK"

if [ $# -lt 3 ]
then
    echo "Replace str1 to str2 in all given files. Backups saved with suffix \"$BACKUP_SUFFIX\"."
    echo "Usage:"
    echo "$0 str1 str2 file(s)..."
    exit 1
fi

S1="$1"
S2="$2"
shift 2

# Escaping the slash character for sed.
SED1="${S1//\//\\\/}"
SED2="${S2//\//\\\/}"
echo "Replacing [$SED1] with [$SED2]"

FILES_MATCHED=0
FILES_REPLACED=0
for FILE in "$@"
do
    if [ ! -f "$FILE" ]
    then
        continue
    fi
    if [ ! -r "$FILE" ]
    then
        echo "WARNING: Unable to read $FILE"
        continue
    fi
    if grep --fixed-strings -- "$S1" "$FILE" >/dev/null 2>&1
    then
        FILES_MATCHED=$(expr $FILES_MATCHED + 1)
        echo "Replacing in $FILE"
        if sed --in-place="$BACKUP_SUFFIX" -- "s/$SED1/$SED2/g" "$FILE"
        then
            FILES_REPLACED=$(expr $FILES_REPLACED + 1)
        else
            echo "ERROR: Unable to replace in $FILE"
        fi
    fi
done

if [ $FILES_REPLACED = 1 ]
then
    echo "1 file changed."
elif [ $FILES_REPLACED != 0 ]
then
    echo "$FILES_REPLACED files changed; backups saved with suffix \"$BACKUP_SUFFIX\"."
else
    echo "No files changed."
fi

if [ $FILES_MATCHED != $FILES_REPLACED ]
then
    echo "Failed to replace in $(expr $FILES_MATCHED - $FILES_REPLACED) file(s) (see above)."
fi
