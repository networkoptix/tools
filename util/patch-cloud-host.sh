#!/bin/bash

CLOUD_HOST_KEY="this_is_cloud_host_name"
FILE_LOCATION="build_environment"
FILE_NAME=".*/\(lib\)?common\.\(a\|dll\|so\)"
LIB_NAME="'common' library"

# From C++ source:
CLOUD_HOST_NAME_WITH_KEY=$(eval echo "this_is_cloud_host_name cloud-test.hdw.mx\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")

#--------------------------------------------------------------------------------------------------

fail()
{
    echo "ERROR: $*" >&2
    exit 1
}

log()
{
    if [ "$VERBOSE" = "1" ]; then
        echo "VERBOSE: $*"
    fi
}

# @return FILES Array of files found by 'find' command.
find_array()
{
    FILES=()
    while IFS= read -r -d $'\0'; do
        FILES+=("$REPLY")
    done < <(find "$@" -print0)
}

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_vms_dir()
{
    if [ "$VMS_DIR" != "" ]; then
        return 1;
    fi

    VMS_DIR=$(pwd)
    while [ $(basename $(dirname "$VMS_DIR")) != "develop" -a "$VMS_DIR" != "/" ]; do
        VMS_DIR=$(dirname "$VMS_DIR")
    done

    if [ "$VMS_DIR" = "/" ]; then
        fail "Run this script from any dir inside nx_vms."
    fi
}

#--------------------------------------------------------------------------------------------------

main()
{
    if [ $# = 0 -o "$1" = "-h" -o "$1" = "--help" ]; then
        echo "Utility to patch the libcommon.so binary in order to replace Cloud Host."
        echo
        echo "Usage:"
        echo
        echo "Show current value:"
        echo "$(basename $0) [--log] --show [path/to/libcommon.so]"
        echo
        echo "Patch with new value:"
        echo "$(basename $0) [--log] 'new_cloud_group' [path/to/libcommon.so]"
        exit 0
    fi

    if [ "$1" == "--verbose" ]; then
        VERBOSE="1"
        shift
    fi

    if [ "$1" != "--show" ]; then
        NEW_CLOUD_HOST="$1"
    fi

    # Determine FILE either from argv[2] or by searching with 'find'.
    if [ $# -ge 2 ]; then
        FILE="$2"
        if [ ! -f "$FILE" ]; then
            fail "Specified file does not exist: $FILE"
        fi
    else
        find_vms_dir

        find_array "$VMS_DIR/$FILE_LOCATION" -regex "$FILE_NAME"

        # Make sure 'find' returned exactly one file.
        if [ ${#FILES[*]} = 0 ]; then
            fail "Unable to find $LIB_NAME in $FILE_LOCATION." >&2
        fi
        if [ ${#FILES[*]} -gt 1 ]; then
            fail "Found ${#FILES[*]} candidates of $LIB_NAME in $FILE_LOCATION." >&2
        fi
        FILE=${FILES[0]}
    fi

    STRING=$(strings --radix=d -d "$FILE" |grep "$CLOUD_HOST_KEY")
    if [ -z "$STRING" ]; then
        fail "'$CLOUD_HOST_KEY' string not found in $FILE"
    fi

    OFFSET=$(echo "$STRING" |awk '{print $1}')
    EXISTING_CLOUD_HOST=$(echo "$STRING" |awk '{print $3}')

    log "Offset: $OFFSET, existing cloud host: $EXISTING_CLOUD_HOST"

    if [ -z "$NEW_CLOUD_HOST" ]; then
        echo "Cloud host: '$EXISTING_CLOUD_HOST' in $(readlink -f "$FILE")".
    else
        BAK_FILE="$FILE.patch-cloud-host.BAK"
        cp "$FILE" "$BAK_FILE"

        PATCH_OFFSET=$(expr "$OFFSET" + ${#CLOUD_HOST_KEY} + 1)
        NUL_OFFSET=$(expr "$PATCH_OFFSET" + ${#NEW_CLOUD_HOST})
        NUL_LEN=$(expr ${#CLOUD_HOST_NAME_WITH_KEY} - ${#CLOUD_HOST_KEY} - 1 - ${#NEW_CLOUD_HOST})
        log "Patch offset: $PATCH_OFFSET, NUL offset: $NUL_OFFSET, NUL len: $NUL_LEN,"
        log "    total len: ${#CLOUD_HOST_NAME_WITH_KEY}, key len: ${#CLOUD_HOST_KEY}"

        # Patching the printable chars.
        echo -ne "$NEW_CLOUD_HOST" |dd bs=1 conv=notrunc seek="$PATCH_OFFSET" of="$FILE" 2>/dev/null \
            || fail "dd 1 failed"

        # Filling the remaining bytes with '\0'.
        dd bs=1 conv=notrunc seek="$NUL_OFFSET" of="$FILE" if=/dev/zero count=1 2>/dev/null \
            || fail "dd 2 failed"

        echo "SUCCESS: Replaced Cloud Host '$EXISTING_CLOUD_HOST' with '$NEW_CLOUD_HOST' in:"
        echo "$FILE"
        echo "Backup saved:"
        echo "$BAK_FILE"
    fi
}

main "$@"
