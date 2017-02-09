#!/bin/bash

CLOUD_HOST_KEY="this_is_cloud_host_name"
FILE_LOCATION="build_environment"
FILE_PATH_REGEX=".*/libcommon\.\(a\|so\)"

# From C++ source:
CLOUD_HOST_NAME_WITH_KEY=$(eval echo \
"this_is_cloud_host_name cloud-test.hdw.mx\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0")

#--------------------------------------------------------------------------------------------------

# Allow 'set -x' to echo the args.
log()
{
    # Allow 'set -x' to echo the args. If not called under 'set -x', do nothing.
    {
        set +x;
        [ ! -z "$VERBOSE" ] && set -x
    } 2>/dev/null
}

# Echo the args replacing full home path with '~', unless the args are already echoed when
# processing this function call under 'set -x'.
writeln()
{
    { set +x; } 2>/dev/null
    if [ -z "$VERBOSE" ]; then
        echo "$@" |sed "s#$HOME/#~/#g"
    else
        set -x
    fi
}

fail()
{
    if [ $fail_MULTILINE ]; then
        for line in "$@"; do
            writeln "ERROR: $line" >&2
        done
    else
        writeln "ERROR: $@" >&2
    fi
    exit 1
}

# [out] FILES Array of files found by 'find' command.
find_FILES_array()
{
    FILES=()
    while IFS="" read -r -d $'\0'; do
        FILES+=("$REPLY")
    done < <(find "$@" -print0)
}

#--------------------------------------------------------------------------------------------------

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in,out] VMS_DIR
find_VMS_DIR()
{
    [ "$VMS_DIR" != "" ] && return 1

    VMS_DIR=$(pwd)
    while [ $(basename $(dirname "$VMS_DIR")) != "develop" -a "$VMS_DIR" != "/" ]; do
        VMS_DIR=$(dirname "$VMS_DIR")
    done

    [ "$VMS_DIR" = "/" ] && fail "Run this script from any dir inside nx_vms."
}

# Search for the file inside the given dir using the given filename regex via 'find'.
# [out] FILE
# [in] FILE_LOCATION
# [in] FILE_PATH_REGEX
find_FILE()
{
    local VMS_DIR
    find_VMS_DIR

    local -a FILES
    find_FILES_array "$VMS_DIR/$FILE_LOCATION" -regex "$FILE_PATH_REGEX"

    # Make sure 'find' returned exactly one file.
    [ ${#FILES[*]} = 0 ] && fail "Unable to find the file to patch in $FILE_LOCATION" >&2
    if [ ${#FILES[*]} -gt 1 ]; then
        fail_MULTILINE=1 fail "Found ${#FILES[*]} candidates to patch in $FILE_LOCATION:" ${FILES[@]}
    fi
    FILE=${FILES[0]}
}

# [in] FILE
save_backup()
{
    local BAK_FILE="$FILE.patch-cloud-host.BAK"
    cp "$FILE" "$BAK_FILE" || fail "failed: cp $FILE $BAK_FILE"
    writeln "Backup saved: $BAK_FILE"
}

# If no CLOUD_HOST_KEY, show the current text, otherwise, patch FILE to set the new text.
# [in] FILE
# [in] CLOUD_HOST_KEY
# [in] NEW_CLOUD_HOST
process_file()
{
    local STRING=$(strings --radix=d -d "$FILE" |grep "$CLOUD_HOST_KEY")
    [ -z "$STRING" ] && fail "'$CLOUD_HOST_KEY' string not found in $FILE"

    local OFFSET=$(echo "$STRING" |awk '{print $1}')
    local EXISTING_CLOUD_HOST=$(echo "$STRING" |awk '{print $3}')

    if [ -z "$NEW_CLOUD_HOST" ]; then
        writeln "Cloud Host is '$EXISTING_CLOUD_HOST' in $FILE"
    elif [ "$NEW_CLOUD_HOST" = "$EXISTING_CLOUD_HOST" ]; then
        writeln "Cloud Host is already '$EXISTING_CLOUD_HOST' in $FILE"
    else
        save_backup

        local PATCH_OFFSET=$(expr "$OFFSET" + ${#CLOUD_HOST_KEY} + 1)
        local NUL_OFFSET=$(expr "$PATCH_OFFSET" + ${#NEW_CLOUD_HOST})
        local NUL_LEN=$(expr ${#CLOUD_HOST_NAME_WITH_KEY} - ${#CLOUD_HOST_KEY} - 1 - ${#NEW_CLOUD_HOST})
        log "CLOUD_HOST_NAME_WITH_KEY len: ${#CLOUD_HOST_NAME_WITH_KEY}"
        log "CLOUD_HOST_KEY len: ${#CLOUD_HOST_KEY}"

        # Patching the printable chars.
        echo -ne "$NEW_CLOUD_HOST" |dd bs=1 conv=notrunc seek="$PATCH_OFFSET" of="$FILE" \
            2>/dev/null || fail "failed: dd of text"

        # Filling the remaining bytes with NUL chars.
        dd bs=1 conv=notrunc seek="$NUL_OFFSET" of="$FILE" if=/dev/zero count="$NUL_LEN" \
            2>/dev/null || fail "failed: dd of NULs"

        writeln "Cloud Host was '$EXISTING_CLOUD_HOST', now is '$NEW_CLOUD_HOST' in $FILE"
    fi
}

show_help_and_exit()
{
    writeln "Utility to patch 'exe' or compiled 'common' lib to replace Cloud Host."
    writeln "Call from anywhere inside 'nx_vms' folder to search for the file."
    writeln
    writeln "Show current value:"
    writeln "    $(basename $0) [--verbose] --show [path/to/binary_file]"
    writeln
    writeln "Patch with new value:"
    writeln "    $(basename $0) [--verbose] 'new_cloud_host' [path/to/binary_file]"
    exit 0
}

main()
{
    [ $# = 0 -o "$1" = "-h" -o "$1" = "--help" ] && show_help_and_exit

    local VERBOSE
    if [ "$1" == "--verbose" ]; then
        VERBOSE="1"
        set -x
        shift
    fi

    local NEW_CLOUD_HOST
    [ "$1" != "--show" ] && NEW_CLOUD_HOST="$1"

    # Determine the file to patch either from argv[2] or by searching.
    local FILE
    if [ $# -ge 2 ]; then
        FILE="$2"
        [ ! -f "$FILE" ] && fail "Specified file does not exist: $FILE"
    else
        find_FILE
    fi

    process_file
}

main "$@"
