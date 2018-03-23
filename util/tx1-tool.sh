#!/bin/bash
source "$(dirname "$0")/utils.sh"

nx_load_config "${RC=".tx1-toolrc"}"

: ${LINUX_TOOL="$(dirname "$0")/linux-tool.sh"}

: ${CLIENT_ONLY=""} #< Prohibit non-client copy commands. Useful for "frankensteins".
: ${SERVER_ONLY=""} #< Prohibit non-server copy commands. Useful for "frankensteins".
: ${DEVELOP_DIR="$HOME/develop"}

: ${BOX_MNT="/tx1"} #< Path at the workstation to which the box root is mounted.
: ${BOX_USER="nvidia"}
: ${BOX_PASSWORD="nvidia"}
: ${BOX_HOST="tx1"} #< Recommented to add "<ip> tx1" to /etc/hosts.
: ${BOX_PORT="22"}
: ${BOX_TERMINAL_TITLE="$BOX_HOST"}
: ${BOX_BACKGROUND_RRGGBB="302000"}
: ${BOX_INSTALL_DIR="/opt/networkoptix"}
: ${BOX_DESKTOP_CLIENT_DIR="$BOX_INSTALL_DIR/desktop_client"}
: ${BOX_MEDIASERVER_DIR="$BOX_INSTALL_DIR/mediaserver"}
: ${BOX_LIBS_DIR="$BOX_INSTALL_DIR/lib"}
: ${BOX_DEVELOP_DIR="/home/$BOX_USER/develop"} #< Mount point at the box for the workstation's "develop".

: ${PACKAGES_BASE_DIR="$DEVELOP_DIR/buildenv/packages"}
: ${PACKAGES_DIR="$PACKAGES_BASE_DIR/tx1"} #< Path at the workstation.
: ${PACKAGES_ANY_DIR="$PACKAGES_BASE_DIR/any"} #< Path at the workstation.
: ${PACKAGE_GCC_LIBS_DIR="$PACKAGES_BASE_DIR/linux-aarch64/gcc-7.2.0/aarch64-unknown-linux-gnu/sysroot/lib"}
: ${PACKAGE_QT="qt-5.6.3"}
: ${PACKAGE_QUAZIP=""} #< Was "quazip-0.7" before 3.2, then made source-only.
: ${PACKAGE_FFMPEG="ffmpeg-3.1.1"}
: ${PACKAGE_SIGAR="sigar-1.7"}

: ${TEGRA_VIDEO_SRC_PATH="artifacts/tx1/tegra_multimedia_api"} #< Relative to VMS_DIR.
: ${VIDEO_DEC_GIE_SRC_PATH="$TEGRA_VIDEO_SRC_PATH/samples/04_video_dec_gie"} #< Relative to VMS_DIR.
: ${NVIDIA_MODELS_PATH="$TEGRA_VIDEO_SRC_PATH/data/model"} #< Demo neural networks. Relative to VMS_DIR.
: ${BOX_NVIDIA_MODELS_DIR="$BOX_MEDIASERVER_DIR/nvidia_models"}

#--------------------------------------------------------------------------------------------------

export TARGET="tx1"

#--------------------------------------------------------------------------------------------------

help_callback()
{
    cat \
<<EOF
Swiss Army Knife for NVidia Tegra ($TARGET): execute various commands.
Use ~/$RC to override workstation-dependent environment vars (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

 $(basename "$0") <options> <command>

$NX_HELP_TEXT_OPTIONS

Here <command> can be one of the following:

 nfs # Mount the box root to $BOX_MNT via NFS.
 sshfs [umount] # Mount/unmount the box root to $BOX_MNT via SSHFS.
 mount # Mount ~/develop to $BOX_DEVELOP_DIR via sshfs. May require workstation password.

 ffmpeg-bins # Copy ffmpeg executables from rdep package to the box $BOX_INSTALL_DIR/.
 tegra_video # Copy libtegra_video.so from rdep package to the box $BOX_LIBS_DIR/.
 copy-s # Copy mediaserver build result (libs and bins) to the box $BOX_INSTALL_DIR/.
 copy-s-all # Copy all mediaserver files including artifacts to the box $BOX_INSTALL_DIR/.
 copy-c # Copy desktop_client build result (libs and bins) to the box $BOX_INSTALL_DIR/.
 copy-c-all # Copy all desktop_client files including artifacts to the box $BOX_INSTALL_DIR/.
 copy # Copy mediaserver and desktop_client build (libs and bins) to the box $BOX_INSTALL_DIR/.
 copy-all # Copy all mediaserver, desktop_client and artifact files to the box $BOX_INSTALL_DIR/.
 copy-s-ut # Copy unit test bins to the box $BOX_MEDIASERVER_DIR/.
 copy-c-ut # Copy unit test bins to the box $BOX_DESKTOP_CLIENT_DIR/.
 lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to the box.
 ini # Create empty .ini files at the box in ~/.config/nx_ini (to be filled with defauls).
 install-tar x.tgz # Install x.tgz to the box via untarring to the root.
 uninstall # Uninstall all nx files from the box.

 go [command args] # Execute a command at the box via ssh, or log in to the box via ssh.
 go-verbose [command args] # Same as "go", but log the command to stdout with "+go " prefix.
 start-s [args] # Run mediaserver exe with [args].
 stop-s # Stop mediaserver via "pkill -9".
 start-c [args] # Run desktop_client exe with [args].
 stop-c # Stop desktop_client via "kill -9".
 run-s-ut mask [args] # Run unit test(s) (use mask \"*_ut\" for all) in server dir.
 run-c-ut mask [args] # Run unit test(s) (use mask \"*_ut\" for all) in desktop_client dir.
 run-tv [args] # Run video_dec_gie with [args].

 tv [args] # Build on the box: libtegra_video_so and video_dec_gie, via "make" with [args].
 tv-ut [cmake-args] # Build and run unit tests on the workstation.
 tv-rdep # Copy libtegra_video.so, tegra_video.h and video_dec_gie to the artifact and "rdep -u".
 tvmp # Copy libtegra_video_metadata_plugin.so to the box $BOX_MEDIASERVER_DIR/bin/plugins/.
 d # Copy libdeepstream_metadata_plugin.so to the box $BOX_MEDIASERVER_DIR/bin/plugins/.

 pack-build <output.tgz> # Prepare tar with build results at the box.
 pack-full <output.tgz> # Prepare tar with complete /opt/networkoptix/ at the box.

 so [-r] [--tree] [<name>] # List all libs used by lib<name>.so (or pwd-guessed common_libs/<name>).
EOF
}

#--------------------------------------------------------------------------------------------------

go_callback()
{
    nx_ssh "$BOX_USER" "$BOX_PASSWORD" "$BOX_HOST" "$BOX_PORT" \
        "$BOX_TERMINAL_TITLE" "$BOX_BACKGROUND_RRGGBB" "$@"
}

# Check that $BOX_MNT is likely to refer to the box root.
check_box_mounted()
{
    if [ ! -d "$BOX_MNT/usr" ]; then
        nx_fail "It seems $BOX_MNT does not refer to the box root dir." \
            "Use $(basename "$0") sshfs or $(basename "$0") nfs to mount."
    fi
}

create_archive() # archive dir command...
{
    local -r ARCHIVE=$(readlink -m "$1"); shift #< Absolute path needed because of later "cd".
    local -r DIR="$1"; shift

    rm -rf "$ARCHIVE" #< Avoid updating an existing archive.
    echo
    echo "Creating $ARCHIVE"
    ( cd "$DIR" && "$@" "$ARCHIVE" * ) #< Subshell prevents "cd" from changing the current dir.
    echo "Done"
}

do_pack() # archive copy_command...
{
    local -r ARCHIVE="$1"; shift
    if [ -z "$ARCHIVE" ]; then
        nx_fail "Archive name is not specified."
    fi

    assert_not_client_only
    assert_not_server_only
    get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

    local -r BOX_MNT=$(mktemp -d) #< Override global var BOX_MNT for the following copy_... calls.

    "$@" || return $?

    if ! create_archive "$ARCHIVE" "$BOX_MNT" tar czf; then
        nx_fail "Unable to create archive (see above) from $BOX_MNT"
    else
        rm -rf "$MNT_DIR"
    fi
}

get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR()
{
    local DIRS=()
    while IFS="" read -r -d $'\n'; do
        DIRS+=("$REPLY")
    done < <("$LINUX_TOOL" print-dirs)

    # Skipping lines starting with "+".
    local -i i=0
    while [[ $i < ${#DIRS[@]} && ${DIRS[$i]} =~ ^\+ ]]
    do
        let i++
    done

    VMS_DIR=${DIRS[$i]}
    [ -z "$VMS_DIR" ] && nx_fail "Unable to get VMS_DIR via $LINUX_TOOL print-dirs"

    CMAKE_BUILD_DIR=${DIRS[(($i + 1))]}
    [ -z "$CMAKE_BUILD_DIR" ] && nx_fail "Unable to get CMAKE_BUILD_DIR via $LINUX_TOOL print-dirs"

    BOX_VMS_DIR="$BOX_DEVELOP_DIR${VMS_DIR#$DEVELOP_DIR}"

    return 0
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
    shopt -s extglob #< Enable extended globs: ?(), *(), +(), @(), !().
    eval FILES_LIST=(${FILE_MASK// /\" \"})
    shopt -u extglob #< Disable extended globs.

    nx_rsync "${FILES_LIST[@]}" "${BOX_MNT}$DST_DIR/" || exit $?

    nx_popd
}

cp_libs() # file_mask [file_mask]...
{
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$CMAKE_BUILD_DIR/lib" "$FILE_MASK" "$BOX_LIBS_DIR"
    done
}

cp_package_libs() # package-name [package-name]...
{
    local PACKAGE
    for PACKAGE in "$@"; do
        if [ ! -z "$PACKAGE" ]; then
            cp_files "$PACKAGES_DIR/$PACKAGE/lib" "*.so*" "$BOX_LIBS_DIR"
        fi
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
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$CMAKE_BUILD_DIR/bin" "$FILE_MASK" "$BOX_MEDIASERVER_DIR/bin"
    done
}

cp_desktop_client_bins() # file_mask [file_mask]...
{
    local FILE_MASK
    for FILE_MASK in "$@"; do
        cp_files "$CMAKE_BUILD_DIR/bin" "$FILE_MASK" "$BOX_DESKTOP_CLIENT_DIR/bin"
    done
}

copy_package_libs()
{
    cp_package_libs \
        "$PACKAGE_FFMPEG" \
        "$PACKAGE_QT" \
        "$PACKAGE_QUAZIP" \
        "$PACKAGE_SIGAR"

    cp_files "$PACKAGE_GCC_LIBS_DIR" "lib{atomic,stdc++}.so*" "$BOX_LIBS_DIR"
}

copy_mediaserver()
{
    cp_mediaserver_bins "mediaserver"
    cp_mediaserver_bins "external.dat" "plugins" "vox"
    ln -s "../lib" "${BOX_MNT}$BOX_MEDIASERVER_DIR/lib" #< rpath: [$ORIGIN/..lib]

    # Tegra analytics.
    cp_package_libs "tegra_video" #< Tegra-specific plugin for video decoding and neural networks.
    cp_files "$VMS_DIR/$NVIDIA_MODELS_PATH" "*" "$BOX_NVIDIA_MODELS_DIR" #< Demo neural networks.
    rm "${BOX_MNT}$BOX_MEDIASERVER_DIR/bin/plugins"/libstub_metadata_plugin.so* #< Stub is not needed.
}

copy_desktop_client()
{
    cp_desktop_client_bins "client-bin"
    cp_desktop_client_bins "fonts" "vox" "help"
    ln -s "../lib" "${BOX_MNT}$BOX_DESKTOP_CLIENT_DIR/lib" #< rpath: [$ORIGIN/..lib]
    cp_files "$PACKAGES_DIR/$PACKAGE_QT/plugins" \
        "{imageformats,platforminputcontexts,platforms,xcbglintegrations,audio}" \
        "$BOX_DESKTOP_CLIENT_DIR/bin"
    cp_files "$PACKAGES_DIR/$PACKAGE_QT" "qml" "$BOX_DESKTOP_CLIENT_DIR/bin"

    # TODO: Remove these symlinks when cmake build is fixed.
    cp_desktop_client_bins "qt.conf"
    local -r PLUGINS_DIR="${BOX_MNT}$BOX_DESKTOP_CLIENT_DIR/plugins"
    mkdir "$PLUGINS_DIR"
    local PLUGIN
    for PLUGIN in audio imageformats platforminputcontexts platforms xcbglintegrations; do
        ln -s "../bin/$PLUGIN" "$PLUGINS_DIR/$PLUGIN"
    done
    ln -s "bin/qml" "${BOX_MNT}$BOX_DESKTOP_CLIENT_DIR/qml"
    # Required structure:
    #     bin/
    #         desktop_client fonts/ help/ vox/
    #     plugins/
    #         audio/ imageformats/ platforminputcontexts/ platforms/ xcbglintegrations/
    #     qml/
    #
    # Actual structure:
    #     bin/
    #         desktop_client fonts/ help/ vox/
    #         qml/
    #         audio/ imageformats/ platforminputcontexts/ platforms/ xcbglintegrations/
}

copy_libs()
{
    cp_libs "*.so!(.debug)"
}

copy_all()
{
    copy_libs
    copy_mediaserver
    copy_desktop_client
    copy_package_libs
}

copy_build()
{
    copy_libs
    cp_mediaserver_bins "mediaserver"
    cp_files "$CMAKE_BUILD_DIR/bin/plugins" "libtegra_video_metadata_plugin.so" \
        "$BOX_MEDIASERVER_DIR/bin/plugins"
    cp_package_libs "tegra_video" #< Tegra-specific plugin for video decoding and neural networks.
    cp_desktop_client_bins "desktop_client"
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

    local LIBS_DIR="$CMAKE_BUILD_DIR/$LIB"

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

install_tar() # archive.tar.gz
{
    local -r INSTALLER=$(readlink -f "$1")
    local -r BOX_INSTALLER="$BOX_DEVELOP_DIR/${INSTALLER#$DEVELOP_DIR}"

    nx_go_verbose sudo tar zxvf "$BOX_INSTALLER" -C /
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
            if [ $# -ge 1 ] && [ "$1" = "umount" ]; then
                fusermount -u "$BOX_MNT" || exit $?
                sudo rmdir "$BOX_MNT" || exit $?
            else
                if [ -d "$BOX_MNT" ]; then
                    fusermount -u "$BOX_MNT" 2>/dev/null
                    sudo rmdir "$BOX_MNT" || exit $?
                fi
                sudo mkdir -p "$BOX_MNT" || exit $?
                sudo chown "$USER" "$BOX_MNT"

                if ! echo "$BOX_PASSWORD" \
                    |nx_verbose sshfs -p "$BOX_PORT" "$BOX_USER@$BOX_HOST":/ "$BOX_MNT" \
                        -o UserKnownHostsFile=/dev/null,StrictHostKeyChecking=no \
                        -o nonempty,password_stdin
                then
                    nx_fail "Unable to mount $BOX_USER@$BOX_HOST:$BOX_PORT to $BOX_MNT"
                fi
                nx_echo "Mounted $BOX_USER@$BOX_HOST:$BOX_PORT to $BOX_MNT:"
                ls "$BOX_MNT"
            fi
            ;;
        mount)
            local BOX_IP=$(ping -q -c 1 -t 1 $BOX_HOST \
                | grep PING | sed -e "s/).*//" | sed -e "s/.*(//")
            local SUBNET=$(echo "$BOX_IP" |awk 'BEGIN { FS = "." }; { print $1 "." $2 }')
            local SELF_IP=$(ifconfig |awk '/inet addr/{print substr($2,6)}' |grep "$SUBNET")
            nx_go umount "$BOX_DEVELOP_DIR" #< Just in case.
            nx_go mkdir -p "$BOX_DEVELOP_DIR" || exit $?

            # TODO: Fix: When using a tunnel, reverse port is "-p 22<IP>" and host "la.hdw.mx".
            # TODO: Fix: "sshfs" does not work via sshpass, but works if executed directly at the box.
            nx_echo
            nx_echo "ATTENTION: Now execute directly at the box (adjust if using a tunnel):"
            echo sshfs "$USER@$SELF_IP:$DEVELOP_DIR" "$BOX_DEVELOP_DIR" -o nonempty,allow_other
            #nx_go sshfs "$USER@$SELF_IP:$DEVELOP_DIR" "$BOX_DEVELOP_DIR" -o nonempty \
                #"[&&]" echo "$DEVELOP_DIR mounted to the box $BOX_DEVELOP_DIR."
            ;;
        #..........................................................................................
        ffmpeg-bins)
            check_box_mounted
            # Debug tools, not included into the distro.
            [ "$CLIENT_ONLY" != "1" ] && cp_mediaserver_package_bins "$PACKAGE_FFMPEG"
            [ "$SERVER_ONLY" != "1" ] && cp_desktop_client_package_bins "$PACKAGE_FFMPEG"
            ;;
        tegra_video)
            assert_not_client_only
            check_box_mounted

            cp_package_libs "tegra_video"
            cp_mediaserver_package_bins "tegra_video" #< Debug tools, not included into the distro.
            ;;
        copy-s)
            assert_not_client_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_libs
            cp_mediaserver_bins "mediaserver"
            ;;
        copy-s-all)
            assert_not_client_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_libs
            copy_mediaserver
            copy_package_libs

            nx_echo "SUCCESS: All mediaserver files copied."
            ;;
        copy-c)
            assert_not_server_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_libs
            cp_desktop_client_bins "client-bin"
            ;;
        copy-c-all)
            assert_not_server_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_libs
            copy_desktop_client
            copy_package_libs

            nx_echo "SUCCESS: All desktop_client files copied."
            ;;
        copy)
            assert_not_client_only
            assert_not_server_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_build
            ;;
        copy-all)
            assert_not_client_only
            assert_not_server_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            copy_all

            nx_echo "SUCCESS: All files copied."
            ;;
        copy-s-ut)
            assert_not_client_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            cp_mediaserver_bins "*_ut"
            ;;
        copy-c-ut)
            assert_not_server_only
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

            cp_desktop_client_bins "*_ut"
            ;;
        lib)
            check_box_mounted
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            if [ "$1" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$1"
            fi
            # NOTE: For some libs there may be no "lib" prefix.
            cp_libs "*$LIB_NAME.so"
            ;;
        ini)
            local INI_DIR="/home/$BOX_USER/.config/nx_ini"
            nx_go_verbose \
                touch "$INI_DIR/nx_media.ini" "[&&]" \
                touch "$INI_DIR/nx_streaming.ini" "[&&]" \
                touch "$INI_DIR/plugins.ini" "[&&]" \
                touch "$INI_DIR/mediaserver.ini" "[&&]" \
                touch "$INI_DIR/tegra_video_metadata_plugin.ini" "[&&]" \
                touch "$INI_DIR/video_dec_gie.ini" "[&&]" \
                touch "$INI_DIR/tegra_video.ini"
            ;;
        install-tar)
            install_tar "$@"
            ;;
        uninstall)
            local -r DIRS_TO_REMOVE=(
                "$BOX_INSTALL_DIR"
            )
            for FILE in "${DIRS_TO_REMOVE[@]}"; do
                nx_go_verbose sudo rm -rf "$FILE" "[||]" true #< Ignore missing files.
            done
            ;;
        #..........................................................................................
        go)
            nx_go "$@"
            ;;
        go-verbose)
            nx_go_verbose "$@"
            ;;
        start-s)
            assert_not_client_only
            nx_go sudo "$BOX_MEDIASERVER_DIR/bin/mediaserver" -e "$@"
            ;;
        stop-s)
            nx_go sudo pkill -9 mediaserver
            ;;
        start-c)
            assert_not_server_only
            nx_go "[ export DISPLAY=:0; ]" "$BOX_DESKTOP_CLIENT_DIR/bin/client-bin" "$@"
            ;;
        stop-c)
            nx_go sudo killall -9 client-bin
            ;;
        run-s-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified."
            local TEST_PATH="$BOX_MEDIASERVER_DIR/bin/$TEST_NAME"
            nx_echo "Running: $TEST_PATH $@"
            nx_go \
                for TEST in $TEST_PATH "[;]" \
                do \
                    echo "[;]" \
                    echo "Running" "[\$TEST]" "[;]" \
                    LD_LIBRARY_PATH="$BOX_LIBS_DIR" "[\$TEST]" "$@" "[|| break;]" \
                done
            ;;
        run-c-ut)
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified. Use \"*_ut\" for all tests."
            local TEST_PATH="$BOX_DESKTOP_CLIENT_DIR/bin/$TEST_NAME"
            nx_echo "Running: $TEST_PATH $@"
            nx_go \
                for TEST in $TEST_PATH "[;]" \
                do \
                    echo "[;]" \
                    echo "Running" "[\$TEST]" "[;]" \
                    LD_LIBRARY_PATH="$BOX_LIBS_DIR" "[\$TEST]" "$@" "[|| break;]" \
                done
            ;;
        run-tv)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            local BOX_SRC_DIR="$BOX_VMS_DIR/$VIDEO_DEC_GIE_SRC_PATH"
            nx_go cd "$BOX_SRC_DIR" "[&&]" ./video_dec_gie "$@"
            ;;
        #..........................................................................................
        tv)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            local BOX_SRC_DIR="$BOX_VMS_DIR/$VIDEO_DEC_GIE_SRC_PATH"
            if [[ $* =~ clean ]]; then
                nx_go make -C "$BOX_SRC_DIR" "$@"
                # No need to attempt copying files.
            else
                nx_go make -C "$BOX_SRC_DIR" "$@" \
                    "[&&]" echo "Compiled OK; copying to $BOX_INSTALL_DIR/..." \
                    "[&&]" cp "$BOX_SRC_DIR/libtegra_video.so" "$BOX_LIBS_DIR/" \
                    "[&&]" cp "$BOX_SRC_DIR/video_dec_gie" "$BOX_MEDIASERVER_DIR/bin/" \
                    "[&&]" echo "SUCCESS: libtegra_video.so and video_dec_gie copied."
            fi
            ;;
        tv-ut)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            local SRC_DIR="$VMS_DIR/$TEGRA_VIDEO_SRC_PATH"
            local TV_TEST_BUILD_DIR="$CMAKE_BUILD_DIR/$TEGRA_VIDEO_SRC_PATH"
            rm -rf "$TV_TEST_BUILD_DIR"
            mkdir -p "$TV_TEST_BUILD_DIR" || return $?
            nx_pushd "$TV_TEST_BUILD_DIR"
            nx_echo "+ cd $TV_TEST_BUILD_DIR"

            nx_verbose cmake "$SRC_DIR" -GNinja || return $?
            nx_verbose cmake --build . "$@" || return $?

            nx_verbose ./tegra_video_ut || return $?

            nx_popd
            rm -rf "$TV_TEST_BUILD_DIR"
            ;;
        tv-rdep)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            local SRC_DIR="$VMS_DIR/$VIDEO_DEC_GIE_SRC_PATH"

            nx_echo "Copying from $SRC_DIR/ to $PACKAGES_DIR/tegra_video/"
            nx_rsync "$SRC_DIR/libtegra_video.so" "$PACKAGES_DIR/tegra_video/lib/" || exit $?
            nx_rsync "$SRC_DIR/tegra_video.h" "$PACKAGES_DIR/tegra_video/include/" || exit $?
            nx_rsync "$SRC_DIR/video_dec_gie" "$PACKAGES_DIR/tegra_video/bin/" || exit $?

            nx_pushd "$PACKAGES_DIR/tegra_video"
            rdep -u && nx_echo "SUCCESS: Deployed to rdep."
            local RESULT=$?
            nx_popd
            return $RESULT
            ;;
        tvmp)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            cp_files "$CMAKE_BUILD_DIR/bin/plugins" "libtegra_video_metadata_plugin.so" \
                "$BOX_MEDIASERVER_DIR/bin/plugins"
            ;;
        d)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR
            cp_files "$CMAKE_BUILD_DIR/bin/plugins" "libdeepstream_metadata_plugin.so" \
                "$BOX_MEDIASERVER_DIR/bin/plugins"
            ;;

        #..........................................................................................
        pack-build)
            do_pack "$1" copy_build
            ;;
        pack-full)
            do_pack "$1" copy_all
            ;;
        #..........................................................................................
        so)
            get_VMS_DIR_and_CMAKE_BUILD_DIR_and_BOX_VMS_DIR

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
            "$LINUX_TOOL" "$COMMAND" "$@"
            ;;
    esac
}

nx_run "$@"
