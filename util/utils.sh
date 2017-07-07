#!/bin/bash

# Utilities to be used in various Nx bash scripts.

#--------------------------------------------------------------------------------------------------
# Low-level utils.

# Call "help" and exit the script if none or typical help command-line arguments are specified.
# Usage: nx_handle_help "$@"
nx_handle_help() # "$@"
{
    if [ $# = 0 -o "$1" = "-h" -o "$1" = "--help" ]; then
        help
        exit 1
    fi
}

# Set the verbose mode and return whether $1 is consumed.
nx_handle_verbose() # "$@" && shift
{
    if [ "$1" == "--verbose" -o "$1" == "-v" ]; then
        NX_VERBOSE="1"
        set -x
        return 0
    else
        return 1
    fi
}

# Set the mode to simulate rsync calls and return whether $1 is consumed.
nx_handle_mock_rsync() # "$@" && shift
{
    if [ "$1" == "--mock-rsync" ]; then
        rsync() #< Define the function which overrides rsync executable name.
        {
            nx_echo
            nx_echo "MOCKED:"
            nx_echo "rsync $*"
            nx_echo
            # Check that all local files exist.
            local FILE
            local I=0
            for FILE in "$@"; do
                 # Check all args not starting with "-" except the last, which is the remote path.
                let I='I+1'
                if [[ $I < $# && $FILE != \-* ]]; then
                    if [ ! -r "$FILE" ]; then
                        nx_fail "Mocked rsync: Cannot access local file: $FILE"
                    fi
                fi
            done
        }
        return 0
    else
        return 1
    fi
}

# Copy the file(s) recursively, showing a progress.
nx_rsync() # rsync_args...
{
    rsync -rlpDh --progress "$@"
}

# Log the args if in verbose mode, otherwise, do nothing.
nx_log() # ...
{
    # Allow "set -x" to echo the args. If not called under "set -x", do nothing, but suppress
    # unneeded logging (bash does not allow to define an empty function, and if ":" is used, it
    # will be logged by "set -x".)
    {
        set +x;
        [ ! -z "$NX_VERBOSE" ] && set -x
    } 2>/dev/null
}

# Log the contents of the file in verbose mode via "sudo cat", otherwise, do nothing.
nx_log_file_contents() # filename
{
    # Args already echoed if called under "set -x", thus, do nothing but suppress unneeded logging.
    {
        set +x;
        local FILE="$1"
        if [ ! -z "$NX_VERBOSE" ]; then
            echo "<<EOF"
            sudo cat "$FILE"
            echo "EOF"
            set -x
        fi
    } 2>/dev/null
}

# Execute the command specified in the args, logging the call with "set -x", unless "set -x" mode
# is already on - in this case, the call of this function with all its args is already logged.
nx_verbose() # "$@"
{
    {
        if [ -z "$NX_VERBOSE" ]; then
            set -x
        else
            set +x
        fi
    } 2>/dev/null

    "$@"

    {
        local RESULT=$?
        if [ -z "$NX_VERBOSE" ]; then
            set +x
        else
            set -x
        fi
        return $RESULT
    } 2>/dev/null
}

nx_show() # VAR_NAME
{
    local VAR_NAME="$1"
    eval local VAR_VALUE="\$$VAR_NAME"
    echo "####### $VAR_NAME: [$VAR_VALUE]"
}

# Echo the args replacing full home path with '~', but do nothing in verbose mode because the args
# are already printed by "set -x".
nx_echo() # ...
{
    { set +x; } 2>/dev/null
    if [ -z "$NX_VERBOSE" ]; then
        echo "$@" |sed "s#$HOME/#~/#g"
    else
        set -x
    fi
}

# Echo the message and additional lines (if any) to stderr and exit the whole script with error.
nx_fail()
{
    nx_echo "ERROR: $1" >&2
    shift

    for LINE in "$@"; do
        nx_echo "    $LINE" >&2
    done
    exit 1
}

# Set the specified variable to the terminal background color (hex), or empty if not supported.
nx_get_background() # RRGGBB_VAR
{
    local RRGGBB_VAR="$1"

    eval "$RRGGBB_VAR="

    # To get terminal background, one should type "\033]11;?\033\\", and the terminal echoes:
    # "\033]11;rgb:RrRr/GgGg/BbBb\033\\", where Rr is Red hex, Gg is Green hex, and Bb is Blue hex.
    # If the terminal does not support it, it will not echo anything in reply.
    exec </dev/tty # Redirect chars generated by the terminal to stdin.
    local OLD_STTY_SETTINGS=$(stty -g)
    stty -echo #< Ask the terminal not to echo the background color request.
    echo -en "\033]11;?\033\\" #< Feed the terminal with the background color request.
    if read -r -d '\' -t 0.05 COLOR; then #< Read the generated chars (if any, use timeout 50 ms).
        eval "$RRGGBB_VAR=\${COLOR:11:2}\${COLOR:16:2}\${COLOR:21:2}"
    fi
    stty "$OLD_STTY_SETTINGS"
}

# Set the terminal background color (hex).
nx_set_background() # RRGGBB
{
    local RRGGBB="$1"

    [ ! -z "$RRGGBB" ] && echo -en "\\e]11;#${RRGGBB}\\a"
}

# Produce colored output: nx_echo "$(nx_red)Red text$(nx_nocolor)"
nx_nocolor()  { echo -en "\033[0m"   ; }
nx_black()    { echo -en "\033[0;30m"; }
nx_dred()     { echo -en "\033[0;31m"; }
nx_dgreen()   { echo -en "\033[0;32m"; }
nx_dyellow()  { echo -en "\033[0;33m"; }
nx_dblue()    { echo -en "\033[0;34m"; }
nx_dmagenta() { echo -en "\033[0;35m"; }
nx_dcyan()    { echo -en "\033[0;36m"; }
nx_lgray()     { echo -en "\033[0;37m"; }
nx_dgray()    { echo -en "\033[1;30m"; }
nx_lred()     { echo -en "\033[1;31m"; }
nx_lgreen()   { echo -en "\033[1;32m"; }
nx_lyellow()  { echo -en "\033[1;33m"; }
nx_lblue()    { echo -en "\033[1;34m"; }
nx_lmagenta() { echo -en "\033[1;35m"; }
nx_lcyan()    { echo -en "\033[1;36m"; }
nx_white()    { echo -en "\033[1;37m"; }

# Set the terminal window title.
nx_set_title()
{
    local TITLE="$*"

    echo -en "\033]0;${TITLE}\007"
}

# Save the current terminal title on the stack.
nx_push_title()
{
    echo -en "\033[22;0t"
}

# Restore the terminal title from the stack.
nx_pop_title()
{
    echo -en "\033[23;0t"
}

# Save the current cursor position.
# ATTENTION: Scrolling does not adjust the saved position, thus, restoring will not be possible.
nx_save_cursor_pos()
{
    echo -en "\033[s"
}

# Sequence to echo to the terminal to restore saved cursor position.
NX_RESTORE_CURSOR_POS="\033[u"

# Restore saved cursor position.
nx_restore_cursor_pos()
{
    echo -en "$NX_RESTORE_CURSOR_POS"
}

nx_pushd() # "$@"
{
    # Do not print pushed dir name.
    # On failure, the error message is printed by pushd.
    pushd "$@" >/dev/null || nx_fail
}

nx_popd()
{
    # Do not print popped dir name.
    popd >/dev/null || nx_fail
}

#--------------------------------------------------------------------------------------------------
# High-level utils, can use low-level utils.

# Execute a command via ssh, or log in via ssh.
#
# Ssh reparses the concatenated args string at the remote host, thus, this function performs the
# escaping of the args, except for the "*" chars (to enable globs) and args in square brackets (to
# enable e.g. combining commands via "[&&]" or redirecting with "[>]").
nx_ssh() # user password host port terminal_title background_rrggbb [command [args...]]
{
    local USER="$1"; shift
    local PASSWORD="$1"; shift
    local HOST="$1"; shift
    local PORT="$1"; shift
    local TERMINAL_TITLE="$1"; shift
    local BACKGROUND_RRGGBB="$1"; shift

    # Concatenate and escape the args except "*" and args in "[]".
    local ARGS=""
    if [ ! -z "$*" ]; then
        for ARG in "$@"; do
            case "$ARG" in
                "["*"]") # Anything in square brackets.
                    ARGS+="${ARG:1:-1} " #< Trim surrounding braces.
                    ;;
                *)
                    printf -v ARG_ESCAPED "%q " "$ARG" #< Perform the escaping.
                    ARGS+="${ARG_ESCAPED//\\\*/*}" #< Append, unescaping all "*".
                    ;;
            esac
        done
        ARGS="${ARGS%?}" #< Trim the last space introduced by printf.
    fi

    local OLD_BACKGROUND
    nx_get_background OLD_BACKGROUND
    nx_set_background "$BACKGROUND_RRGGBB"
    nx_push_title
    nx_set_title "$TERMINAL_TITLE"

    sshpass -p "$PASSWORD" ssh -p "$PORT" -t "$USER@$HOST" \
        -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no `#< Do not use known_hosts` \
        ${ARGS:+"$ARGS"} `#< Omit arg if empty`

    RESULT=$?

    nx_pop_title
    nx_set_background "$OLD_BACKGROUND"

    return "$RESULT"
}

nx_sshfs() # user password host port host_path mnt_point
{
    local USER="$1"; shift
    local PASSWORD="$1"; shift
    local HOST="$1"; shift
    local PORT="$1"; shift
    local HOST_PATH="$1"; shift
    local MNT_POINT="$1"; shift

    echo "$BOX_PASSWORD" |sshfs -p "$PORT" "$USER@$HOST":"$HOST_PATH" "$MNT_POINT" \
        -o nonempty,password_stdin \
        -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no `# Do not use known_hosts`
}

# Return in the specified variable the array of files found by 'find' command.
nx_find_files() # FILES_ARRAY_VAR find_args...
{
    local FILES_ARRAY_VAR="$1"
    shift

    local FILES_ARRAY=()
    while IFS="" read -r -d $'\0'; do
        FILES_ARRAY+=("$REPLY")
    done < <(find "$@" -print0)
    eval "$FILES_ARRAY_VAR"'=("${FILES_ARRAY[@]}")'
}

# Search for the file inside the given dir using the given filename regex via 'find'.
# If more than one file is found, fail with the message including the file list.
nx_find_file() # FILE_VAR dir regex [file_description_for_error_message]
{
    local FILE_VAR="$1"
    local FILE_LOCATION="$2"
    local FILE_PATH_REGEX="$3"
    local FILE_DESCRIPTION="${4:-$3}"

    local FILES=()
    nx_find_files FILES "$FILE_LOCATION" -regex "$FILE_PATH_REGEX"

    # Make sure "find" returned exactly one file.
    if [ ${#FILES[*]} = 0 ]; then
        nx_fail "Unable to find $FILE_DESCRIPTION in $FILE_LOCATION"
    fi
    if [ ${#FILES[*]} -gt 1 ]; then
        nx_fail "Found ${#FILES[*]} files instead of $FILE_DESCRIPTION in $FILE_LOCATION:" \
            ${FILES[@]}
    fi

    eval "$FILE_VAR=\${FILES[0]}"
}

# If the specified variable is not set, scan from the current dir upwards up to but not including
# the specified parent dir, and return its child dir in the variable.
# @param error_message_if_not_found If specified, on failure a fatal error is produced, otherwise,
#     return 1 and set DIR_VAR to the current dir.
nx_find_parent_dir() # DIR_VAR parent/dir [error_message_if_not_found]
{
    local DIR_VAR="$1"
    local PARENT_DIR="$2"
    local ERROR_MESSAGE="$3"

    local DIR=$(eval "echo \$$DIR_VAR")

    if [ "$DIR" != "" ]; then
        return 0
    fi

    DIR=$(pwd)
    while [ "$(basename "$(dirname "$DIR")")" != "$PARENT_DIR" -a "$DIR" != "/" ]; do
        DIR=$(dirname "$DIR")
    done

    local RESULT=0
    if [ "$DIR" = "/" ]; then
        if [ -z "$ERROR_MESSAGE" ]; then
            RESULT=1
            DIR=$(pwd)
        else
            nx_fail "$ERROR_MESSAGE"
        fi
    fi

    eval "$DIR_VAR=\$DIR"
    return $RESULT
}

# Check that the specified file exists. Needed to support globs in the filename.
nx_glob_exists()
{
    [ -e "$1" ]
}

# Execute "sudo dd" showing a progress, return the status of "dd".
nx_sudo_dd() # dd_args...
{
    # Redirect to a subshell to enable capturing the pid of the "sudo" process.
    # Print only lines containing "copied", suppress '\n' (to avoid scrolling).
    # Spaces are added to overwrite the remnants of a previous text.
    # "-W interactive" runs awk without input buffering for certain versions of awk; suppressing
    # awk's stderr is used to avoid its warning in case it does not support this option.
    sudo dd "$@" 2> >(awk -W interactive \
        "\$0 ~ /copied/ {printf \"${NX_RESTORE_CURSOR_POS}%s                 \", \$0}" \
        2>/dev/null) &
    local SUDO_PID=$!

    # On ^C, kill "dd" which is the child of "sudo".
    trap "trap - SIGINT; sudo pkill -9 -P $SUDO_PID" SIGINT

    nx_save_cursor_pos
    while sudo kill -0 $SUDO_PID; do #< Checking that "sudo dd" is still running.
        # Ask "dd" to print the progress; break if "dd" is finished.
        sudo kill -USR1 $SUDO_PID || break

        sleep 1
    done

    # Avoid "%" appearing in the console.
    echo

    wait $SUDO_PID #< Get the Status Code of finished "dd".
}

# Source the specified file (typically with settings), return whether it exists.
nx_load_config() # "${CONFIG='.<tool-name>rc'}"
{
    local FILE="$1"

    local PATH="$HOME/$FILE"
    [ -f "$PATH" ] && source "$PATH"
}

# Call after sourcing this script.
nx_run()
{
    nx_handle_verbose "$@" && shift
    nx_handle_help "$@"
    nx_handle_mock_rsync "$@" && shift

    main "$@"

    local RESULT=$?
    if [ $RESULT != 0 ]; then
        nx_echo "The script FAILED (status $RESULT)."
    fi
    return $RESULT
}
