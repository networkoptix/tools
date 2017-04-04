#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".tx1-toolrc"}"

: ${CLIENT_ONLY=""} #< Prohibit non-client copy commands. Useful for "frankensteins".
: ${SERVER_ONLY=""} #< Prohibit non-server copy commands. Useful for "frankensteins".
: ${DEVELOP_DIR="$HOME/develop"}
: ${TARGET_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the target dir.
: ${BUILD_CONFIG=""} #< Path component after "bin/" and "lib/".
: ${MVN_BUILD_DIR=""} #< Path component at the workstation; can be empty.
: ${CORES_ARG="-j12"}
: ${MAKE_TOOL="Ninja"} #< Used for cmake generator and (lower-case) for "m" command.

: ${BOX_MNT="/tx1"} #< Path at the workstation to which the box root is mounted.
: ${BOX_USER="ubuntu"}
: ${BOX_PASSWORD="ubuntu"}
: ${BOX_HOST="tx1"} #< Recommented to add "<ip> tx1" to /etc/hosts.
: ${BOX_PORT="22"}
: ${BOX_TERMINAL_TITLE="$BOX_HOST"}
: ${BOX_BACKGROUND_RRGGBB="302000"}
: ${BOX_INSTALL_DIR="/opt/networkoptix"}
: ${BOX_DESKTOP_CLIENT_DIR="$BOX_INSTALL_DIR/desktop_client"}
: ${BOX_MEDIASERVER_DIR="$BOX_INSTALL_DIR/mediaserver"}
: ${BOX_LIBS_DIR="$BOX_INSTALL_DIR/lib"}
: ${BOX_DEVELOP_DIR="/develop"} #< Mount point at the box for the workstation develop dir.
: ${BOX_PACKAGES_SRC_DIR="$BOX_DEVELOP_DIR/third_party/tx1"} #< Should be mounted at the box.

: ${PACKAGES_SRC_DIR="$DEVELOP_DIR/third_party/tx1"} #< Path at the workstation.
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/tx1-aarch64"} #< Path at the workstation.
: ${PACKAGE_QT="qt-5.6.2"}
: ${PACKAGE_QUAZIP="quazip-0.7"}
: ${PACKAGE_FFMPEG="ffmpeg-3.1.1"}
: ${PACKAGE_OPENLDAP="openldap-2.4.42"}
: ${PACKAGE_SASL2="sasl2-2.1.26"}
: ${PACKAGE_SIGAR="sigar-1.7"}

# Config for maven instead of cmake:
#TARGET_SUFFIX="/build_environment/target-tx1"
#BUILD_CONFIG="debug"
#PACKAGES_DIR="$HOME/develop/buildenv/packages/tx1-arm"
#PACKAGE_QT="qt-5.6.1"
#MVN_BUILD_DIR="arm-tx1"
#BOX_LIBS_DIR="/opt/networkoptix/desktop_client/lib"

#--------------------------------------------------------------------------------------------------

BIN="bin"
LIB="lib"
if [ ! -z "$BUILD_CONFIG" ]; then
    BIN="$BIN/$BUILD_CONFIG"
    LIB="$LIB/$BUILD_CONFIG"
fi

PACKAGES_ANY_DIR="$DEVELOP_DIR/buildenv/packages/any"

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

ffmpeg-bins # Copy ffmpeg executables from rdep package to the box $BOX_INSTALL_DIR.
tegra_video # Copy libtegra_video.so from rdep package to the box $BOX_LIBS_DIR.
copy-s # Copy mediaserver build result (libs and bins) to the box $BOX_INSTALL_DIR.
copy-s-all # Copy all mediaserver files including artifacts to the box $BOX_INSTALL_DIR.
copy-c # Copy desktop_client build result (libs and bins) to the box $BOX_INSTALL_DIR.
copy-c-all # Copy all desktop_client files including artifacts to the box $BOX_INSTALL_DIR.
copy # Copy mediaserver and desktop_client build result (libs and bins) to the box $BOX_INSTALL_DIR.
copy-all # Copy all mediaserver and desktop_client files including artifacts to the box $BOX_INSTALL_DIR.
copy-s-ut # Copy unit test bins to the box $BOX_MEDIASERVER_DIR.
copy-c-ut # Copy unit test bins to the box $BOX_DESKTOP_CLIENT_DIR.
server # Copy mediaserver_core lib to the box.
lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to the box.
ini # Create empty .ini files at the box in /tmp (to be filled with defauls).

ssh [command args] # Execute a command at the box via ssh, or log in to the box via ssh.
start-s [args] # Run mediaserver exe with [args].
stop-s # Stop mediaserver via "kill -9".
start-c [args] # Run desktop_client exe with [args].
stop-c # Stop desktop_client via "kill -9".
run-s-ut test_name [args] # Run the unit test in server dir with strict expectations.
run-c-ut test_name [args] # Run the unit test in desktop_client dir with strict expectations.

clean # Delete all build dirs.
mvn [args] # Call maven with the required platorm and box.
cmake [args] # Call cmake in cmake build dir with the required platorm/box parameters.
m [args] # Call the configured make tool in cmake build dir.

so [-r] [--tree] [<name>] # List all libs used by lib<name>.so (or pwd-guessed common_libs/<name>).
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at the box via ssh, or log in to the box via ssh.
box() # args...
{
    nx_ssh "$BOX_USER" "$BOX_PASSWORD" "$BOX_HOST" "$BOX_PORT" \
        "$BOX_TERMINAL_TITLE" "$BOX_BACKGROUND_RRGGBB" "$@"
}

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR $(basename "$DEVELOP_DIR") \
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

cp_files() # src_dir file_mask dst_dir
{
    local SRC_DIR="$1"; shift
    local FILE_MASK="$1"; shift
    local DST_DIR="$1"; shift

    nx_echo "Rsyncing $(nx_lyellow)$FILE_MASK$(nx_nocolor)" \
        "from $(nx_lcyan)$SRC_DIR/$(nx_nocolor)" \
        "to $(nx_lgreen)$DST_DIR/$(nx_nocolor)"

    mkdir -p "${BOX_MNT}$DST_DIR" || exit $?

    nx_pushd "$SRC_DIR"

    # Here eval expands globs and braces to the array, after we enquote spaces (if any).
    eval FILES_LIST=(${FILE_MASK// /\" \"})

    nx_rsync "${FILES_LIST[@]}" "${BOX_MNT}$DST_DIR/" || exit $?

    nx_popd
}

cp_libs() # file_mask [file_mask]...
{
    find_VMS_DIR
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$VMS_DIR$TARGET_SUFFIX/$LIB" "$FILE_MASK" "$BOX_LIBS_DIR"
    done
}

cp_package_libs() # package-name [package-name]...
{
    local PACKAGE
    for PACKAGE in "$@"; do
        cp_files "$PACKAGES_DIR/$PACKAGE/lib" "*.so*" "$BOX_LIBS_DIR"
    done
}

cp_mediaserver_package_bins() # package-name [package-name]...
{
    local PACKAGE
    for PACKAGE in "$@"; do
        cp_files "$PACKAGES_DIR/$PACKAGE/bin" "*" "$BOX_MEDIASERVER_DIR/bin"
    done
}

cp_desktop_client_package_bins() # package-name [package-name]...
{
    local PACKAGE
    for PACKAGE in "$@"; do
        cp_files "$PACKAGES_DIR/$PACKAGE/bin" "*" "$BOX_DESKTOP_CLIENT_DIR/bin"
    done
}

cp_mediaserver_bins() # file_mask [file_mask]...
{
    find_VMS_DIR
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$VMS_DIR$TARGET_SUFFIX/$BIN" "$FILE_MASK" "$BOX_MEDIASERVER_DIR/bin"
    done
}

cp_desktop_client_bins() # file_mask [file_mask]...
{
    find_VMS_DIR
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$VMS_DIR$TARGET_SUFFIX/$BIN" "$FILE_MASK" "$BOX_DESKTOP_CLIENT_DIR/bin"
    done
}

clean()
{
    find_VMS_DIR
    nx_pushd "$VMS_DIR"

    nx_echo "Deleting: $VMS_DIR$TARGET_SUFFIX"
    rm -r "$VMS_DIR$TARGET_SUFFIX"

    if [ ! -z "$MVN_BUILD_DIR" ]; then
        local BUILD_DIRS=()
        nx_find_files BUILD_DIRS -type d -name "$MVN_BUILD_DIR"
        local DIR
        for DIR in "${BUILD_DIRS[@]}"; do
            nx_echo "Deleting: $DIR"
            rm -r "$DIR"
        done
    fi

    nx_popd
}

do_mvn() # "$@"
{
    mvn -Dbox=tx1 -Darch=arm "$@"
}

assert_not_client_only()
{
    if [ "$CLIENT_ONLY" = "1" ]; then
        nx_fail "Non-client command attempted while config \"~/$CONFIG\" specifies CLIENT_ONLY=1."
    fi
}

assert_not_server_only()
{
    if [ "$SERVER_ONLY" = "1" ]; then
        nx_fail "Non-server command attempted while config \"~/$CONFIG\" specifies SERVER_ONLY=1."
    fi
}

getSoDeps() # libname.so
{
    local LIB="$1"
    readelf -d "$LIB" |grep 'Shared library:' |sed 's/.*\[//' |sed 's/\]//'
}

so() # /*RECURSIVE*/0|1 /*TREE*/0|1 libname.so [indent]
{
    local RECURSIVE=$1; shift
    local TREE=$1; shift
    local LIB="$1"; shift
    local INDENT="$1"; shift

    local LIBS_DIR="$VMS_DIR$TARGET_SUFFIX/$LIB"

    local DEPS=$(getSoDeps "$LIBS_DIR/$LIB")

    local DEP
    for DEP in $DEPS; do
        if [ $TREE = 1 ]; then
            nx_echo "$INDENT$DEP"
        else
            nx_echo "$DEP"
        fi
        if [[ $RECURSIVE = 1 && -f "$LIBS_DIR/$DEP" ]]; then #< DEP is nx lib.
            so $RECURSIVE $TREE "$DEP" "$INDENT    "
        fi
    done
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"; shift
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

            echo "$BOX_PASSWORD" |sshfs -p "$BOX_PORT" "$BOX_USER@$BOX_HOST":/ "$BOX_MNT" \
                -o nonempty,password_stdin
            ;;
        #..........................................................................................
        ffmpeg-bins)
            # Debug tools, not included into the distro.
            [ "$CLIENT_ONLY" != "1" ] && cp_mediaserver_package_bins "$PACKAGE_FFMPEG"
            [ "$SERVER_ONLY" != "1" ] && cp_desktop_client_package_bins "$PACKAGE_FFMPEG"
            ;;
        tegra_video)
            assert_not_client_only
            cp_package_libs "tegra_video"
            cp_mediaserver_package_bins "tegra_video" #< Debug tools, not included into the distro.
            ;;
        copy-s)
            assert_not_client_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_mediaserver_bins "mediaserver"
            ;;
        copy-s-all)
            assert_not_client_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_mediaserver_bins "mediaserver"

            box ln -s "../lib" "$BOX_MEDIASERVER_DIR/lib" #< rpath: [$ORIGIN/..lib]

            cp_package_libs "tegra_video"

            cp_package_libs \
                "$PACKAGE_FFMPEG" \
                "$PACKAGE_QT" \
                "$PACKAGE_QUAZIP" \
                "$PACKAGE_OPENLDAP" \
                "$PACKAGE_SASL2" \
                "$PACKAGE_SIGAR"

            cp_mediaserver_bins "external.dat" "plugins" "vox" "nvidia_models"

            nx_echo "SUCCESS: All mediaserver files copied."
            ;;
        copy-c)
            assert_not_server_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_desktop_client_bins "desktop_client"
            ;;
        copy-c-all)
            assert_not_server_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_desktop_client_bins "desktop_client"

            box ln -s "../lib" "$BOX_DESKTOP_CLIENT_DIR/lib" #< rpath: [$ORIGIN/..lib]

            cp_desktop_client_bins "fonts" "vox" "help"

            cp_package_libs \
                "$PACKAGE_FFMPEG" \
                "$PACKAGE_QT" \
                "$PACKAGE_QUAZIP" \
                "$PACKAGE_OPENLDAP" \
                "$PACKAGE_SASL2" \
                "$PACKAGE_SIGAR"

            cp_files "$PACKAGES_DIR/$PACKAGE_QT/plugins" \
                "{imageformats,platforminputcontexts,platforms,xcbglintegrations,audio}" \
                "$BOX_DESKTOP_CLIENT_DIR/bin"
            cp_files "$PACKAGES_DIR/$PACKAGE_QT" "qml" "$BOX_DESKTOP_CLIENT_DIR/bin"

            nx_echo "SUCCESS: All desktop_client files copied."
            ;;
        copy)
            assert_not_client_only
            assert_not_server_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_mediaserver_bins "mediaserver"
            cp_desktop_client_bins "desktop_client"
            ;;
        copy-all)
            assert_not_client_only
            assert_not_server_only
            find_VMS_DIR
            cp_libs "*.so*"
            cp_mediaserver_bins "mediaserver"
            cp_desktop_client_bins "desktop_client"

            box ln -s "../lib" "$BOX_MEDIASERVER_DIR/lib" #< rpath: [$ORIGIN/..lib]
            box ln -s "../lib" "$BOX_DESKTOP_CLIENT_DIR/lib" #< rpath: [$ORIGIN/..lib]

            cp_desktop_client_bins "fonts" "vox" "help"
            cp_package_libs "tegra_video"

            cp_package_libs \
                "$PACKAGE_FFMPEG" \
                "$PACKAGE_QT" \
                "$PACKAGE_QUAZIP" \
                "$PACKAGE_OPENLDAP" \
                "$PACKAGE_SASL2" \
                "$PACKAGE_SIGAR"

            cp_mediaserver_bins "external.dat" "plugins" "vox" "nvidia_models"

            cp_files "$PACKAGES_DIR/$PACKAGE_QT/plugins" \
                "{imageformats,platforminputcontexts,platforms,xcbglintegrations,audio}" \
                "$BOX_DESKTOP_CLIENT_DIR/bin"
            cp_files "$PACKAGES_DIR/$PACKAGE_QT" "qml" "$BOX_DESKTOP_CLIENT_DIR/bin"

            nx_echo "SUCCESS: All files copied."
            ;;
        copy-s-ut)
            assert_not_client_only
            find_VMS_DIR
            cp_mediaserver_bins "*_ut"
            ;;
        copy-c-ut)
            assert_not_server_only
            find_VMS_DIR
            cp_desktop_client_bins "*_ut"
            ;;
        server)
            assert_not_client_only
            cp_libs "libmediaserver_core.so*"
            ;;
        lib)
            if [ "$1" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$1"
            fi
            cp_libs "lib$LIB_NAME.so*"
            ;;
        ini)
            box touch /tmp/nx_media.ini "[&&]" \
                touch /tmp/analytics.ini "[&&]" \
                touch /tmp/tegra_video.ini
            ;;
        #..........................................................................................
        ssh)
            box "$@"
            ;;
        start-s)
            assert_not_client_only
            box sudo "$BOX_MEDIASERVER_DIR/bin/mediaserver" -e "$@"
            ;;
        stop-s)
            box sudo killall -9 mediaserver
            ;;
        start-c)
            assert_not_server_only
            box sudo DISPLAY=:0 "$BOX_DESKTOP_CLIENT_DIR/bin/desktop_client" "$@"
            ;;
        stop-c)
            box sudo killall -9 desktop_client
            ;;
        run-s-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified."
            local TEST_PATH="$BOX_MEDIASERVER_DIR/ut/$TEST_NAME"
            nx_echo "Running: $TEST_PATH $@"
            box LD_LIBRARY_PATH="$BOX_LIBS_DIR" "$TEST_PATH" "$@"
            ;;
        run-c-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified."
            local TEST_PATH="$BOX_DESKTOP_CLIENT_DIR/ut/$TEST_NAME"
            nx_echo "Running: $TEST_PATH $@"
            box LD_LIBRARY_PATH="$BOX_LIBS_DIR" "$TEST_PATH" "$@"
            ;;
        run-tv)
            local BOX_SRC_DIR="$BOX_PACKAGES_SRC_DIR/tegra_multimedia_api/samples/04_video_dec_gie"
            box cd "$BOX_SRC_DIR" "[&&]" ./video_dec_gie "$@"
            ;;
        #..........................................................................................
        tv)
            local BOX_SRC_DIR="$BOX_PACKAGES_SRC_DIR/tegra_multimedia_api/samples/04_video_dec_gie"
            box make -C "$BOX_SRC_DIR" "$@" \
                "[&&]" echo "Compiled OK; copying to $BOX_INSTALL_DIR..." \
                "[&&]" cp "$BOX_SRC_DIR/libtegra_video.so" "$BOX_LIBS_DIR/" \
                "[&&]" cp "$BOX_SRC_DIR/video_dec_gie" "$BOX_MEDIASERVER_DIR/bin/" \
                "[&&]" echo "SUCCESS: libtegra_video.so and video_dec_gie copied."
            ;;
        tv-rdep)
            local SRC_DIR="$PACKAGES_SRC_DIR/tegra_multimedia_api/samples/04_video_dec_gie"
            nx_rsync "$SRC_DIR/libtegra_video.so" "$PACKAGES_DIR/tegra_video/lib/" || exit $?
            nx_rsync "$SRC_DIR/tegra_video.h" "$PACKAGES_DIR/tegra_video/include/" || exit $?
            nx_rsync "$SRC_DIR/video_dec_gie" "$PACKAGES_DIR/tegra_video/bin/" || exit $?
            cd "$PACKAGES_DIR/tegra_video" || exit $?
            rdep -u && nx_echo "SUCCESS: Deployed to rdep."
            ;;
        #..........................................................................................
        clean)
            clean
            ;;
        mvn)
            do_mvn "$@"
            ;;
        cmake)
            find_VMS_DIR
            local CMAKE_BUILD_DIR="$VMS_DIR$TARGET_SUFFIX"
            mkdir -p "$CMAKE_BUILD_DIR"
            nx_pushd "$CMAKE_BUILD_DIR"

            cmake "$@" -G$MAKE_TOOL \
                -DCMAKE_TOOLCHAIN_FILE="$VMS_DIR/cmake/toolchain/tx1-aarch64.cmake" "$VMS_DIR"

            local RESULT=$?
            nx_popd
            return $RESULT
            ;;
        m)
            find_VMS_DIR
            local CMAKE_BUILD_DIR="$VMS_DIR$TARGET_SUFFIX"
            mkdir -p "$CMAKE_BUILD_DIR"
            nx_pushd "$CMAKE_BUILD_DIR"

            ${MAKE_TOOL,,} "$CORES_ARG" "$@"

            local RESULT=$?
            nx_popd
            return $RESULT
            ;;
        #..........................................................................................
        so)
            find_VMS_DIR

            local RECURSIVE=0
            if [ "$1" = "-r" ]; then
                RECURSIVE=1
                shift
            fi

            local TREE=0
            if [ "$1" = "--tree" ]; then
                TREE=1
                shift
            fi

            if [ "$1" = "" ]; then
                find_LIB_DIR
                local LIB_NAME=$(basename "$LIB_DIR")
            else
                local LIB_NAME="$1"
            fi

            if [ $TREE = 1 ]; then
                so $RECURSIVE $TREE "lib$LIB_NAME.so"
            else
                so $RECURSIVE $TREE "lib$LIB_NAME.so" |sort |uniq
            fi
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
