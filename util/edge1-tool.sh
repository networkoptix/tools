#!/bin/bash
source "$(dirname "$0")/utils.sh"

nx_load_config "${CONFIG=".edge1-toolrc"}"

: ${LINUX_TOOL="$(dirname "$0")/linux-tool.sh"}
: ${TARGET_DEVICE="edge1"} #< Target device for CMake.

: ${BOX_MNT="/edge1"}
: ${BOX_USER="root"}
: ${BOX_INITIAL_PASSWORD="cpro0109"}
: ${BOX_PASSWORD="qweasd123"}
: ${BOX_HOST="edge1"} #< Recommented to add "<ip> edge1" to /etc/hosts.
: ${BOX_PORT="23"}
: ${BOX_TERMINAL_TITLE="$BOX_HOST"}
: ${BOX_BACKGROUND_RRGGBB="300000"}
: ${BOX_INSTALL_DIR="/opt/networkoptix"}
: ${BOX_MEDIASERVER_DIR="$BOX_INSTALL_DIR/mediaserver"}
: ${BOX_LOGS_DIR="/sdcard/mserver.data/log"}
: ${BOX_LIBS_DIR="$BOX_INSTALL_DIR/lib"}
: ${BOX_DEVELOP_DIR="/root/develop"} #< Mount point at the box for the workstation develop dir.

: ${DEVELOP_DIR="$HOME/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/isd_s2"} #< Path at the workstation.
: ${QT_DIR="$DEVELOP_DIR/buildenv/packages/isd_s2/qt-5.6.1"} #< Path at the workstation.
: ${BUILD_CONFIG="debug"}
: ${TARGET_IN_VMS_DIR="build_environment/target-edge1"} #< Path component at the workstation.
: ${BUILD_DIR="arm-edge1"} #< Path component at the workstation.
: ${PACKAGE_SUFFIX=""}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the cmake build dir.

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for DW Edge Camera ($TARGET_DEVICE): execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

$(basename "$0") [--verbose] <command>

Here <command> can be one of the following:

 nfs # Mount the box root to $BOX_MNT via NFS.
 mount # Mount ~/develop to the box /root/develop via sshfs. May require workstation password.

 copy-s # Copy mediaserver libs, bins and scripts to the box $BOX_INSTALL_DIR.
 copy-ut # Copy all libs and unit test bins to the box $BOX_INSTALL_DIR.
 lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to the box.
 logs # Create empty -out.flag files at the box'es log dir to trigger logs with respective names.
 logs-clean # Delete all .log files at the box'es log dir.
 install-tar [mvn|cmake|x.tar.gz] # Install x.tar.gz to the box via untarring to the root.
 uninstall # Uninstall all nx files from the box.

 go [command args] # Execute a command at the box via telnet, or log in to the box via telnet.
 start-s [args] # Run mediaserver via "/etc/init.d/S99networkoptix-mediaserver start [args]".
 stop-s # Stop mediaserver via "/etc/init.d/networkoptix-mediaserver stop".

 # Commands which call linux-tool.sh with the proper target:
 clean # Delete cmake build dir and all maven build dirs.
 mvn [Release] [args] # Call maven.
 gen [Release] [cmake-args] # Perform cmake generation. For linux-x64, use target "linux".
 build # Build via "cmake --build <dir>".
 cmake [Release] [gen-args] # Perform cmake generation, then build via "cmake --build".
 build-installer [Release] [mvn] # Build installer using cmake or maven.
 test-installer [Release] [checksum] [no-build] [mvn] orig/archives/dir # Test if built matches orig.
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at the box via ssh, or log in to the box via ssh.
go() # "$@"
{
    nx_telnet "$BOX_USER" "$BOX_PASSWORD" "$BOX_HOST" "$BOX_PORT" \
        "$BOX_TERMINAL_TITLE" "$BOX_BACKGROUND_RRGGBB" "$@"
}

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
# [out] BOX_VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" \
        "Run this script from any dir inside your nx_vms repo dir."
    BOX_VMS_DIR="$BOX_DEVELOP_DIR/${VMS_DIR#$DEVELOP_DIR}"
}

# Deduce CMake build dir out of VMS_DIR and targetDevice (box). Examples:
# nx -> nx-build-edge1
# nx-edge1 -> nx-edge1-build.
# /C/develop/nx -> nx-win-build-linux
# [in] VMS_DIR
get_CMAKE_BUILD_DIR()
{
    case "$VMS_DIR" in
        *-"$TARGET_DEVICE")
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
            ;;
        "$WIN_DEVELOP_DIR"/*)
            VMS_DIR_NAME=${VMS_DIR#$WIN_DEVELOP_DIR/} #< Removing the prefix.
            CMAKE_BUILD_DIR="$DEVELOP_DIR/$VMS_DIR_NAME-win$BUILD_SUFFIX-$TARGET_DEVICE"
            ;;
        *)
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX-$TARGET_DEVICE"
            ;;
    esac
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

    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/lib/$BUILD_CONFIG/$MASK" \
        "$BOX_LIBS_DIR" "$DESCRIPTION" "$VMS_DIR"
}

cp_sysroot_libs() # file_mask description
{
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$PACKAGES_DIR/sysroot/usr/lib/arm-linux-gnueabihf/$MASK" \
        "$BOX_LIBS_DIR" "$DESCRIPTION" "packages/isd_s2/sysroot"
}

cp_mediaserver_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/$BUILD_CONFIG/$MASK" \
        "$BOX_MEDIASERVER_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
}

cp_script_with_customization_filtering() # src dst
{
    SCRIPT_SRC="$1"
    SCRIPT_DST="$2"

    cat "$SCRIPT_SRC" |sed -e 's/${deb\.customization\.company\.name}/networkoptix/g' \
        >"$SCRIPT_DST" || exit $?

    chmod +x "$SCRIPT_DST" || exit $?
}

cp_scripts_dir() # src dst
{
    SCRIPTS_SRC="$1"
    SCRIPTS_DST="$2"

    nx_echo "Copying scripts from $SCRIPTS_SRC"

    for SCRIPT in "$SCRIPTS_SRC"/*; do
        cp_script_with_customization_filtering "$SCRIPT" "$SCRIPTS_DST/$(basename $SCRIPT)"
    done
}

copy_scripts()
{
    find_VMS_DIR
    local DIR="$VMS_DIR/edge_firmware/rpi/maven"
    cp_scripts_dir "$DIR/isd/etc/init.d" "${BOX_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/filter-resources/etc/init.d" "${BOX_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/isd/opt/networkoptix/mediaserver/var/scripts" \
        "${BOX_MNT}$BOX_MEDIASERVER_DIR/var/scripts"
}

find_INSTALLER() # .ext [mvn|cmake|archive.file]
{
    local -r EXT="$1"; shift

    get_CMAKE_BUILD_DIR
    local -r CMAKE_DIR="$CMAKE_BUILD_DIR/edge_firmware"
    local -r MVN_DIR="$VMS_DIR/edge_firmware/isd/target-edge1"

    local BUILD="" #< mvn|cmake
    if [ $# -ge 1 ]; then
        case "$1" in
            mvn|cmake)
                BUILD="$1"
                ;;
            *)
                INSTALLER="$1"
                ;;
        esac
    else
        # Auto-detect cmake vs msn, producing an error if none or both are present.
        if [ -d "$CMAKE_DIR" ] && [ ! -d "$MVN_DIR" ]; then # cmake only
            BUILD=cmake
        elif [ -d "$MVN_DIR" ] && [ ! -d "$CMAKE_DIR" ]; then # mvn only
            BUILD=mvn
        elif [ ! -d "$MVN_DIR" ] && [ ! -d "$CMAKE_DIR" ]; then # none
            nx_fail "Unable to find either installer directory: maven [$MVN_DIR] or cmake [$CMAKE_DIR]."
        else # both
            nx_fail "Both maven and cmake installer directories exist, specify manually."
        fi
    fi

    case $BUILD in
        mvn) nx_find_file INSTALLER "Installer $EXT (maven)" "$MVN_DIR" -name "*$EXT" ;;
        cmake) nx_find_file INSTALLER "Installer $EXT (cmake)" "$CMAKE_DIR" -name "*$EXT" ;;
        *) `# Already found.` ;;
    esac

    nx_echo "Installing $INSTALLER"
}

install_tar() # "$@"
{
    find_VMS_DIR
    find_INSTALLER ".tar.gz" "$@"
    local -r BOX_INSTALLER="$BOX_DEVELOP_DIR/${INSTALLER#$DEVELOP_DIR}"

    go tar zxvf "$BOX_INSTALLER" -C /
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

            sudo mount -o nolock "$BOX_HOST:/" "$BOX_MNT" &&
                echo "Box mounted via nfs to $BOX_MNT"
            ;;
        mount)
            local BOX_IP=$(ping -q -c 1 -t 1 $BOX_HOST | grep PING | sed -e "s/).*//" | sed -e "s/.*(//")
            local SUBNET=$(echo "$BOX_IP" |awk 'BEGIN { FS = "." }; { print $1 "." $2 }')
            local SELF_IP=$(ifconfig |awk '/inet addr/{print substr($2,6)}' |grep "$SUBNET")
            go umount "$BOX_DEVELOP_DIR" #< Just in case.
            go mkdir -p "$BOX_DEVELOP_DIR" || exit $?

            go mount -o nolock "$SELF_IP:$DEVELOP_DIR" "$BOX_DEVELOP_DIR"
            #    && echo "$DEVELOP_DIR mounted to the box $BOX_DEVELOP_DIR."
            ;;
        #..........................................................................................
        copy-scripts)
            check_box_mounted
            copy_scripts
            ;;
        copy-s)
            check_box_mounted
            find_VMS_DIR

            mkdir -p "${BOX_MNT}$BOX_LIBS_DIR"

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "media_db_util" "media_db_util"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            copy_scripts

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_DIR/lib/*.so*" "$BOX_LIBS_DIR" "Qt libs" "$QT_DIR"
            #cp_mediaserver_bins "vox" "mediaserver vox"

            # Server configuration does not need to be copied.
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/isd/$BOX_MEDIASERVER_DIR/etc" "$BOX_MEDIASERVER_DIR" "etc" "$VMS_DIR"
            ;;
        copy-ut)
            check_box_mounted
            find_VMS_DIR
            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"
            cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/$BUILD_CONFIG/*_ut" \
                "$BOX_MEDIASERVER_DIR/ut" "unit tests" "$VMS_DIR"
            ;;
        lib)
            check_box_mounted
            if [ "$1" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$1"
            fi
            cp_libs "lib$LIB_NAME.so*" "lib $LIB_NAME"
            ;;
        logs)
            go \
                mkdir -p "$BOX_LOGS_DIR" "[&&]" \
                touch "$BOX_LOGS_DIR/S99networkoptix-mediaserver-out.flag" "[&&]" \
                touch "$BOX_LOGS_DIR/mediaserver-out.flag"
            ;;
        logs-clean)
            go rm -rf "$BOX_LOGS_DIR/*.log"
            ;;
        install-tar)
            install_tar "$@"
            ;;
        uninstall)
            local -r DIRS_TO_REMOVE=(
                /opt/networkoptix
                /usr/local/apps/networkoptix
                /sdcard/networkoptix_service
                /etc/init.d/S99networkoptix-mediaserver
                /opt/digitalwatchdog
                /usr/local/apps/digitalwatchdog
                /sdcard/digitalwatchdog_service
                /etc/init.d/S99digitalwatchdog-mediaserver
                /sdcard/mserver.data
                /sdcard/swapfile
                /sdcard/cores
                "/root/mediaserver*.gdb-bt"
            )
            go rm -rf ${DIRS_TO_REMOVE[@]}
            ;;
        #..........................................................................................
        do)
            go "$@"
            ;;
        start-s)
            go /etc/init.d/S99networkoptix-mediaserver start "$@"
            ;;
        stop-s)
            go /etc/init.d/S99networkoptix-mediaserver stop
            ;;
        #..........................................................................................
        clean)
            "$LINUX_TOOL" clean "$TARGET_DEVICE" "$@"
            ;;
        mvn)
            "$LINUX_TOOL" mvn "$TARGET_DEVICE" "$@"
            ;;
        gen)
            "$LINUX_TOOL" gen "$TARGET_DEVICE" "$@"
            ;;
        build)
            "$LINUX_TOOL" build "$TARGET_DEVICE" "$@"
            ;;
        cmake)
            "$LINUX_TOOL" cmake "$TARGET_DEVICE" "$@"
            ;;
        build-installer)
            "$LINUX_TOOL" build-installer "$TARGET_DEVICE" "$@"
            ;;
        test-installer)
            "$LINUX_TOOL" test-installer "$TARGET_DEVICE" "$@"
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
