#!/bin/bash
source "$(dirname $0)/utils.sh"

#--------------------------------------------------------------------------------------------------
# Config

CONFIG=".tx1-toolrc"
nx_load_config "$CONFIG" #< Load config and assign defaults to values missing in config.
: ${BOX_MNT:="/tx1"} #< Path at the workstation to which the box root is mounted.
: ${BOX_USER:="ubuntu"}
: ${BOX_PASSWORD:="ubuntu"}
: ${BOX_HOST:="tx1"} #< Recommented to add "<ip> tx1" to /etc/hosts.
: ${BOX_TERMINAL_TITLE:="$BOX_HOST"}
: ${BOX_BACKGROUND_RRGGBB:="302000"}
: ${DEVELOP_DIR:="$HOME/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/tx1-aarch64"} #< Path at the workstation.
: ${QT_DIR="$PACKAGES_DIR/qt-5.6.2"} #< Path at the workstation.

#--------------------------------------------------------------------------------------------------
# Const

# Paths at the box.
BOX_INSTALL_DIR="/opt/networkoptix"
BOX_LITE_CLIENT_DIR="$BOX_INSTALL_DIR/lite_client"
BOX_MEDIASERVER_DIR="$BOX_INSTALL_DIR/mediaserver"

# BOX_LIBS_DIR can be pre-defined before running this script.
if [ -z "$BOX_LIBS_DIR" ]; then
    BOX_LIBS_DIR="$BOX_INSTALL_DIR/lib"
else
    nx_echo "ATTENTION: BOX_LIBS_DIR overridden to $BOX_LIBS_DIR"
fi

# PACKAGE_SUFFIX can be pre-defined before running this script.
if [ -z "$PACKAGE_SUFFIX" ]; then
    PACKAGE_SUFFIX=""
else
    nx_echo "ATTENTION: PACKAGE_SUFFIX defined as $PACKAGE_SUFFIX"
fi

# Path components at the workstation.
BUILD_DIR="aarch64"
TARGET_IN_VMS_DIR="build_environment/target"

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for NVidia Tegra (Tx1): execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

$(basename "$0") [--verbose] <command>

Here <command> can be one of the following:

nfs # Mount the box root to $BOX_MNT via NFS.
sshfs # Mount the box root to $BOX_MNT via SSHFS.

copy-s # Copy mediaserver libs and bins to the box $BOX_INSTALL_DIR.
copy-ut # Copy all libs and unit test bins to the box $BOX_INSTALL_DIR.
server # Copy mediaserver_core lib to the box.
common # Copy common lib to the box.
lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to the box.
ini # Create empty .ini files at the box in /tmp (to be filled with defauls).

ssh [command args] # Execute a command at the box via ssh, or log in to the box via ssh.
start-s [args] # Run mediaserver via "/etc/init.d/networkoptix-mediaserver start [args]".
stop-s # Stop mediaserver via "/etc/init.d/networkoptix-mediaserver stop".
run-ut [test-name args] # Run the specified unit test with strict expectations.
start [args] # Run mediaserver and mobile_client via "/etc/init.d/networkoptix-* start [args]".
stop # Stop mediaserver and mobile_client via "/etc/init.d/networkoptix-* stop".

clean # Delete all build dirs recursively.
rebuild [args] # Perform clean, then "mvn clean package ... [args]".
mvn [args] # Call maven with the required platorm and box.
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at the box via ssh, or log in to the box via ssh.
box() # args...
{
    nx_ssh "$BOX_USER" "$BOX_PASSWORD" "$BOX_HOST" "$BOX_TERMINAL_TITLE" "$BOX_BACKGROUND_RRGGBB" \
        "$@"
}

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" \
        "Run this script from any dir inside your nx_vms repo dir."
}

# If not done yet, scan from current dir upwards to find "common_libs" dir; set LIB_DIR to its
# inner dir.
# [in][out] LIB_DIR
find_LIB_DIR()
{
    nx_find_parent_dir LIB_DIR "common_libs" \
        "Either specify lib name or cd to common_libs/<lib_name>."
}

cp_files()
{
    local FILE_MASK="$1"
    local FILES_DST="$2"
    local FILES_DESCRIPTION="$3"
    local FILES_SRC_DESCRIPTION="$4"

    nx_echo "Copying $FILES_DESCRIPTION from $FILES_SRC_DESCRIPTION to $FILES_DST/"

    mkdir -p "${BOX_MNT}$FILES_DST" || exit $?

    # Here eval expands globs and braces to the array, after we enquote spaces (if any).
    eval FILE_LIST=(${FILE_MASK// /\" \"})

    nx_rsync "${FILE_LIST[@]}" "${BOX_MNT}$FILES_DST/" || exit $?
}

cp_libs() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"

    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/lib/debug/$MASK" \
        "$BOX_LIBS_DIR" "$DESCRIPTION" "$VMS_DIR"
}

cp_mediaserver_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/debug/$MASK" \
        "$BOX_MEDIASERVER_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
}

clean()
{
    find_VMS_DIR
    cd "$VMS_DIR"
    local BUILD_DIRS=()
    nx_find_files BUILD_DIRS -type d -name "$BUILD_DIR"
    local DIR
    for DIR in "${BUILD_DIRS[@]}"; do
        nx_echo "Deleting: $DIR"
        rm -r "$DIR"
    done
}

do_mvn() # "$@"
{
    mvn -Dbox=tx1-aarch64 -Darch=aarch64 "$@"
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        nfs)
            sudo umount "$BOX_MNT"
            sudo rm -rf "$BOX_MNT" || exit $?
            sudo mkdir -p "$BOX_MNT" || exit $?
            sudo chown "$USER" "$BOX_MNT"

            sudo mount -o nolock "$BOX_HOST:/" "$BOX_MNT"
            ;;
        sshfs)
            sudo umount "$BOX_MNT"
            sudo rm -rf "$BOX_MNT" || exit $?
            sudo mkdir -p "$BOX_MNT" || exit $?
            sudo chown "$USER" "$BOX_MNT"

            echo "$BOX_PASSWORD" |sshfs "$BOX_USER@$BOX_HOST":/ "$BOX_MNT" -o nonempty,password_stdin
            ;;
        #..........................................................................................
        copy-s)
            find_VMS_DIR

            local LIBS_DIR="${BOX_MNT}$BOX_LIBS_DIR"
            mkdir -p "$LIBS_DIR/tegra"
            mkdir -p "$LIBS_DIR/libgtk2.0-0"
            mkdir -p "$LIBS_DIR/stubs"
            mkdir -p "$LIBS_DIR/libgtk-3-0"

            cp_libs "*.so*" "all libs"

            mkdir -p "${BOX_MNT}$BOX_MEDIASERVER_DIR/bin"
            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$QT_DIR/lib/*.so*" "$BOX_LIBS_DIR" "Qt libs" "$QT_DIR"
            #cp_mediaserver_bins "vox" "mediaserver vox"

            exit 0
            ;;
        copy-ut)
            find_VMS_DIR
            cp_libs "*.so*" "all libs"
            cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/debug/*_ut" \
                "$BOX_MEDIASERVER_DIR/ut" "unit tests" "$VMS_DIR"
            ;;
        server)
            cp_libs "libmediaserver_core.so*" "lib mediaserver_core"
            ;;
        common)
            cp_libs "libcommon.so*" "lib common"
            ;;
        lib)
            if [ "$1" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$1"
            fi
            cp_libs "lib$LIB_NAME.so*" "lib $LIB_NAME"
            ;;
        ini)
            box \
                touch /tmp/mobile_client.ini "[&&]" \
                touch /tmp/nx_media.ini \
            ;;
        #..........................................................................................
        ssh)
            box "$@"
            ;;
        start-s)
            box sudo LD_LIBRARY_PATH="$BOX_LIBS_DIR" "$BOX_MEDIASERVER_DIR/bin/mediaserver" -e "$@"
            ;;
        stop-s)
            box sudo kill -9 mediaserver
            ;;
        run-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified."
            echo "Running: $TEST_NAME $@"
            box LD_LIBRARY_PATH="$BOX_LIBS_DIR" "$BOX_MEDIASERVER_DIR/ut/$TEST_NAME" "$@"
            ;;
        #..........................................................................................
        clean)
            clean
            ;;
        rebuild)
            clean || exit $?
            do_mvn clean package "$@"
            ;;
        mvn)
            do_mvn "$@"
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
