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
        exit 0
    fi
}

# Set the verbose mode and return 0 if $1 is "--verbose"; return 1 otherwise.
# Usage: nx_set_VERBOSE "$@" && shift
nx_handle_verbose() # "$@"
{
    if [ "$1" == "--verbose" -o "$1" == "-v" ]; then
        NX_VERBOSE="1"
        set -x
        return 0
    else
        return 1
    fi
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

#--------------------------------------------------------------------------------------------------
# High-level utils, can use low-level utils.

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
nx_find_file() # FILE_VAR dir regex file_description_for_error_message
{
    local FILE_VAR="$1"
    local FILE_LOCATION="$2"
    local FILE_PATH_REGEX="$3"
    local FILE_DESCRIPTION="$4"

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
nx_find_parent_dir() # DIR_VAR parent/dir error_message_if_not_found
{
    local DIR_VAR="$1"
    local PARENT_DIR="$2"
    local ERROR_MESSAGE="$3"

    local DIR=$(eval "echo \$$DIR_VAR")

    if [ "$DIR" != "" ]; then
        return
    fi

    echo $PARENT_DIR
    DIR=$(pwd)
    echo $DIR
    while [ "$(basename "$(dirname "$DIR")")" != "$PARENT_DIR" -a "$DIR" != "/" ]; do
        echo $DIR
        DIR=$(dirname "$DIR")
    done

    if [ "$DIR" = "/" ]; then
        nx_fail "$ERROR_MESSAGE"
    fi

    eval "$DIR_VAR=\$DIR"
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
    # "-W interactive" run awk without input buffering.
    # Spaces are added to overwrite the remnants of a previous text.
    sudo dd "$@" 2> >(awk -W interactive \
        "\$0 ~ /copied/ {printf \"${NX_RESTORE_CURSOR_POS}%s                 \", \$0}") &
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

# Copy the file(s) recursively, showing a progress.
nx_rsync() # rsync_args...
{
    rsync -r -ah --progress "$@"
}

# Source the specified file (typically with settings), return whether it exists.
nx_load_config() # rc_file
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
    main "$@"
}
