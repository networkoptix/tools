#!/bin/bash
source "$(dirname $0)/utils.sh"

# Collection of various convenient commands used for NVidia Tegra (Tx1) development.

#--------------------------------------------------------------------------------------------------
# Config

nx_load_config ".tx1rc" #< Load config and assign defaults to values missing in config.
: ${TX1_MNT:="/tx1"}
: ${TX1_USER:="ubuntu"}
: ${TX1_PASSWORD:="ubuntu"}
: ${TX1_HOST:="tx1"} #< Recommented to add "<ip> tx1" to /etc/hosts.
: ${TX1_TERMINAL_TITLE:="$TX1_HOST"}
: ${TX1_BACKGROUND_RRGGBB:="302000"}
: ${DEVELOP_DIR:="$HOME/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/tx1"} #< Path at this workstation.
: ${QT_PATH="$DEVELOP_DIR/buildenv/packages/tx1/qt-5.6.2"} #< Path at this workstation.

#--------------------------------------------------------------------------------------------------
# Const

# Paths at tx1.
TX1_INSTALL_DIR="/opt/networkoptix"
TX1_LITE_CLIENT_DIR="$TX1_INSTALL_DIR/lite_client"
TX1_MEDIASERVER_DIR="$TX1_INSTALL_DIR/mediaserver"

# TX1_LIBS_DIR can be pre-defined before running this script.
if [ -z "$TX1_LIBS_DIR" ]; then
    TX1_LIBS_DIR="$TX1_INSTALL_DIR/lib"
else
    nx_echo "ATTENTION: TX1_LIBS_DIR overridden to $TX1_LIBS_DIR"
fi

# PACKAGE_SUFFIX can be pre-defined before running this script.
if [ -z "$PACKAGE_SUFFIX" ]; then
    PACKAGE_SUFFIX=""
else
    nx_echo "ATTENTION: PACKAGE_SUFFIX defined as $PACKAGE_SUFFIX"
fi

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for NVidia Tegra (Tx1): execute various commands.
Use ~/.tx1rc to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:
$(basename "$0") [--verbose] <command>
Here <command> can be one of the following:

nfs # Mount tx1 root to $TX1_MNT via NFS.
sshfs # Mount tx1 root to $TX1_MNT via SSHFS.

copy-s # Copy mediaserver libs and bins to tx1 $TX1_INSTALL_DIR.
copy-ut # Copy all libs and unit test bins to tx1 $TX1_INSTALL_DIR.
server # Copy mediaserver_core lib to tx1.
common # Copy common lib to tx1.
lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to tx1.
ini # Create empty .ini files @tx1 in /tmp (to be filled with defauls).

ssh [command args] # Execute a command at tx1 via ssh, or log in to tx1 via ssh.
start-s [args] # Run mediaserver via "/etc/init.d/networkoptix-mediaserver start [args]".
stop-s # Stop mediaserver via "/etc/init.d/networkoptix-mediaserver stop".
run-ut [test-name args] # Run the specified unit test with strict expectations.
start [args] # Run mediaserver and mobile_client via "/etc/init.d/networkoptix-* start [args]".
stop # Stop mediaserver and mobile_client via "/etc/init.d/networkoptix-* stop".

rebuild [args] # Perform "mvn clean package ... [args]", including unit tests.
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at tx1 via ssh, or log in to tx1 via ssh.
tx1() # args...
{
    nx_ssh "$TX1_USER" "$TX1_PASSWORD" "$TX1_HOST" "$TX1_TERMINAL_TITLE" "$TX1_BACKGROUND_RRGGBB" \
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

    mkdir -p "${TX1_MNT}$FILES_DST" || exit $?

    # Here eval expands globs and braces to the array, after we enquote spaces (if any).
    eval FILE_LIST=(${FILE_MASK// /\" \"})

    nx_rsync "${FILE_LIST[@]}" "${TX1_MNT}$FILES_DST/" || exit $?
}

cp_libs() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"

    cp_files "$VMS_DIR/build_environment/target-tx1/lib/debug/$MASK" \
        "$TX1_LIBS_DIR" "$DESCRIPTION" "$VMS_DIR"
}

cp_mediaserver_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/build_environment/target-tx1/bin/debug/$MASK" \
        "$TX1_MEDIASERVER_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        nfs)
            sudo umount "$TX1_MNT"
            sudo rm -rf "$TX1_MNT" || exit $?
            sudo mkdir -p "$TX1_MNT" || exit $?
            sudo chown "$USER" "$TX1_MNT"

            sudo mount -o nolock tx1:/ "$TX1_MNT"
            exit $?
            ;;
        sshfs)
            sudo umount "$TX1_MNT"
            sudo rm -rf "$TX1_MNT" || exit $?
            sudo mkdir -p "$TX1_MNT" || exit $?
            sudo chown "$USER" "$TX1_MNT"

            echo "$TX1_PASSWORD" |sshfs root@"$TX1_HOST":/ "$TX1_MNT" -o nonempty,password_stdin
            exit $?
            ;;
        #..........................................................................................
        copy-s)
            find_VMS_DIR

            # In case of taking mobile_client from different branch and overriding TX1_LIBS_DIR:
            mkdir -p "${TX1_MNT}$TX1_LIBS_DIR"

            cp_libs "*.so*" "all libs"

            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "media_db_util" "media_db_util"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_PATH/lib/*.so*" "$TX1_LIBS_DIR" "Qt libs" "$QT_PATH"
            #cp_mediaserver_bins "vox" "mediaserver vox"

            # Server configuration does not need to be copied.
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/tx1/$TX1_MEDIASERVER_DIR/etc" "$TX1_MEDIASERVER_DIR" "etc" "$VMS_DIR"

            exit 0
            ;;
        copy-ut)
            find_VMS_DIR
            cp_libs "*.so*" "all libs"
            cp_files "$VMS_DIR/build_environment/target-tx1/bin/debug/*_ut" \
                "$TX1_MEDIASERVER_DIR/ut" "unit tests" "$VMS_DIR"
            exit $?
            ;;
        server)
            cp_libs "libmediaserver_core.so*" "lib mediaserver_core"
            exit $?
            ;;
        common)
            cp_libs "libcommon.so*" "lib common"
            exit $?
            ;;
        lib)
            if [ "$1" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$1"
            fi
            cp_libs "lib$LIB_NAME.so*" "lib $LIB_NAME"
            exit $?
            ;;
        ini)
            tx1 \
                touch /tmp/mobile_client.ini "[&&]" \
                touch /tmp/nx_media.ini \
            exit $?
            ;;
        #..........................................................................................
        ssh)
            tx1 "$@"
            exit $?
            ;;
        start-s)
            tx1 /etc/init.d/networkoptix-mediaserver start "$@"
            exit $?
            ;;
        stop-s)
            tx1 /etc/init.d/networkoptix-mediaserver stop
            exit $?
            ;;
        run-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && fail "Test name not specified."
            echo "Running: $TEST_NAME $@"
            tx1 LD_LIBRARY_PATH="$TX1_MEDIASERVER_DIR/lib" \
                "$TX1_MEDIASERVER_DIR/ut/$TEST_NAME" "$@"
            exit $?
            ;;
        #..........................................................................................
        rebuild)
            find_VMS_DIR
            cd "$VMS_DIR"
            mvn clean package \
                -Dbox=tx1-aarch64 -Darch=aarch64 -Dutb -Dcloud.url='cloud-test.hdw.mx' "$@"
            exit $?
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
