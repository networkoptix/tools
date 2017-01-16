#!/bin/bash

# Collection of various convenient commands used for Banana Pi (NX1) development.

# Mount point of Banana Pi root at this workstation.
BPI="/bpi"

PACKAGES_DIR="$HOME/develop/buildenv/packages/bpi"
PACKAGES_SRC_DIR="$HOME/develop/third_party/bpi"
PACKAGES_SRC_BPI_DIR="/root/develop/third_party/bpi" # Expected to be mounted at bpi.
NX_BPI_DIR="/opt/networkoptix"
LITE_CLIENT_DIR="$NX_BPI_DIR/lite_client"
MEDIASERVER_DIR="$NX_BPI_DIR/mediaserver"

# LIBS_DIR can be predefined.
if [ -z "$LIBS_DIR" ]; then
    LIBS_DIR="$NX_BPI_DIR/lib"
else
    echo "ATTENTION: LIBS_DIR overridden to $LIBS_DIR"
    LIBS_DIR_OVERRIDEN=1
fi

# PACKAGE_SUFFIX can be predefined.
if [ -z "$PACKAGE_SUFFIX" ]; then
    PACKAGE_SUFFIX=
else
    echo "ATTENTION: PACKAGE_SUFFIX defined as $PACKAGE_SUFFIX"
fi

QT_PATH="buildenv/packages/bpi/qt-5.6.2"

#--------------------------------------------------------------------------------------------------

echo_with_nice_paths()
{
    echo "$1" |sed -e "s#$HOME#~#g"
}

# [in] FILES_LIST
pack()
{
    ARCHIVE="$1"

    if [ "$ARCHIVE" = "" ]; then
        echo "ERROR: Archive filename to create not specified."
        exit 1
    fi

    bpi "tar --absolute-names -czvf $ARCHIVE $FILES_LIST"
}

pack_full()
{
    FILES_LIST="$NX_BPI_DIR"
    pack "$*"
}

pack_short()
{
    # Pack build results and bpi-specific artifacts from third_party.

    FILES_LIST=" \
        $LIBS_DIR/libappserver2.so \
        $LIBS_DIR/libclient_core.so \
        $LIBS_DIR/libcloud_db_client.so \
        $LIBS_DIR/libcommon.so \
        $LIBS_DIR/libconnection_mediator.so \
        $LIBS_DIR/libmediaserver_core.so \
        $LIBS_DIR/libudt.so \
        $LIBS_DIR/libnx_audio.so \
        $LIBS_DIR/libnx_email.so \
        $LIBS_DIR/libnx_fusion.so \
        $LIBS_DIR/libnx_media.so \
        $LIBS_DIR/libnx_network.so \
        $LIBS_DIR/libnx_streaming.so \
        $LIBS_DIR/libnx_utils.so \
        $LIBS_DIR/libnx_vms_utils.so \
		\
        $LIBS_DIR/ldpreloadhook.so \
        $LIBS_DIR/libcedrus.so \
        $LIBS_DIR/libpixman-1.so \
        $LIBS_DIR/libproxydecoder.so \
        $LIBS_DIR/libvdpau_sunxi.so \
        $LIBS_DIR/libUMP.so \
	    \
        $LITE_CLIENT_DIR/bin/mobile_client \
        $LITE_CLIENT_DIR/bin/video/videonode/libnx_bpi_videonode_plugin.so \
		$MEDIASERVER_DIR/bin/mediaserver \
		$MEDIASERVER_DIR/bin/media_db_util \
		$MEDIASERVER_DIR/bin/external.dat \
		$MEDIASERVER_DIR/bin/plugins \
		/etc/init.d/networkoptix* \
		/etc/init.d/nx* \
		$MEDIASERVER_DIR/var/scripts \
    "
    pack "$*"
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
        echo "ERROR: Run this script from any dir inside nx_vms."
        exit 1
    fi
}

# If not done yet, scan from current dir upwards to find "common_libs" dir; set LIB_DIR to its
# inner dir.
# [in][out] LIB_DIR
find_lib_dir()
{
    if [ "$LIB_DIR" != "" ]; then
        return 1;
    fi

    LIB_DIR=$(pwd)
    while [ $(basename $(dirname "$LIB_DIR")) != "common_libs" -a "$LIB_DIR" != "/" ]; do
        LIB_DIR=$(dirname "$LIB_DIR")
    done

    if [ "$LIB_DIR" = "/" ]; then
        echo "ERROR: Either specify lib name or cd to common_libs/<lib_name>."
        exit 1
    fi
}

cp_files()
{
    FILES_SRC="$1"
    FILES_LIST="$2"
    FILES_DST="$3"
    FILES_DESCRIPTION="$4"
    FILES_SRC_DESCRIPTION="$5"

    echo_with_nice_paths "Copying $FILES_DESCRIPTION from $FILES_SRC_DESCRIPTION to $FILES_DST/"

    sudo mkdir -p "${BPI}$FILES_DST" || exit 1

    # Here eval performs expanding of globs, including "{,}".
    FILES_LIST_EXPANDED=$(eval echo "$FILES_SRC/$FILES_LIST")

    sudo cp -r $FILES_LIST_EXPANDED "${BPI}$FILES_DST/" || exit 1
}

cp_libs()
{
    find_vms_dir
    cp_files "$VMS_DIR/build_environment/target-bpi/lib/debug" "$1" "$LIBS_DIR" "$2" "$VMS_DIR"
}

cp_sysroot_libs()
{
    cp_files "$PACKAGES_DIR/sysroot/usr/lib/arm-linux-gnueabihf" \
        "$1" "$LIBS_DIR" "$2" "packages/bpi/sysroot"
}

cp_lite_client_bins()
{
    find_vms_dir
    cp_files "$VMS_DIR/build_environment/target-bpi/bin/debug" "$1" "$LITE_CLIENT_DIR/bin" "$2" "$VMS_DIR"
}

cp_mediaserver_bins()
{
    find_vms_dir
    cp_files "$VMS_DIR/build_environment/target-bpi/bin/debug" "$1" "$MEDIASERVER_DIR/bin" "$2" "$VMS_DIR"
}

cp_script_with_customization_filtering()
{
    SCRIPT_SRC="$1"
    SCRIPT_DST="$2"

    # Here tee is required because ">/bpi/..." requires root access.
    sudo cat "$SCRIPT_SRC" |sed -e 's/${deb\.customization\.company\.name}/networkoptix/g' |sudo tee "$SCRIPT_DST" >/dev/null

    sudo chmod +x "$SCRIPT_DST" || exit 1
}

cp_scripts()
{
    SCRIPTS_SRC="$1"
    SCRIPTS_DST="$2"

    echo_with_nice_paths "Copying scripts from $SCRIPTS_SRC"

    for SCRIPT in $SCRIPTS_SRC/*; do
        cp_script_with_customization_filtering "$SCRIPT" "$SCRIPTS_DST/$(basename $SCRIPT)"
    done
}

copy_scripts()
{
    find_vms_dir
    cp_scripts "$VMS_DIR/edge_firmware/rpi/maven/bpi/etc/init.d" "${BPI}/etc/init.d"
    cp_scripts "$VMS_DIR/edge_firmware/rpi/maven/filter-resources/etc/init.d" "${BPI}/etc/init.d"
    cp_scripts "$VMS_DIR/edge_firmware/rpi/maven/bpi/opt/networkoptix/mediaserver/var/scripts" \
        "${BPI}$MEDIASERVER_DIR/var/scripts"
}

#--------------------------------------------------------------------------------------------------
show_help_and_exit()
{
    echo "Swiss Army Knife for Banana Pi (NX1): execute various commands. Uses 'bpi' script."
    echo "Usage: run from any dir inside the proper nx_vms dir:"
    echo $0 "<command>"
    echo "Here <command> can be one of the following:"
    echo
    echo "mount - Mount bpi root to $BPI via NFS."
    echo "sshfs - Mount bpi root to $BPI via SSHFS."
    echo
    echo "copy-s - Copy mediaserver libs, bins and scripts to bpi $NX_BPI_DIR."
    echo "copy-c - Copy mobile_client libs and bins to bpi $NX_BPI_DIR."
    echo "client - Copy mobile_client exe to bpi."
    echo "server - Copy mediaserver_core lib to bpi."
    echo "lib [<name>] - Copy the specified (or pwd-guessed common_libs/<name>) library (e.g. nx...) to bpi."
	echo "ini - Create empty .ini files @bpi in /tmp (to be filled with defauls)."
    echo
    echo "exec ... - Pass all args to 'bpi'; can be used to check args passing: 'b exec args ...'"
    echo "run ... - Execute mobile_client @bpi via '$NX_BPI_DIR/mediaserver/var/scripts/start_lite_client'."
    echo "kill - Stop mobile_client via 'killall mobile_client'."
    echo "start-s ... - Start mediaserver @bpi via '/etc/init.d/networkoptix-mediaserver start'."
    echo "stop-s - Stop mediaserver @bpi via '/etc/init.d/networkoptix-mediaserver stop'."
    echo "start-s ... - Start mobile_client @bpi via '/etc/init.d/networkoptix-lite-client start'."
    echo "stop-s - Stop mobile_client @bpi via '/etc/init.d/networkoptix-lite-client stop'."
    echo "start ... - Start mediaserver and mobile_client @bpi via '/etc/init.d/networkoptix-* start'."
    echo "stop - Stop mediaserver and mobile_client @bpi via '/etc/init.d/networkoptix-* stop'."
    echo
    echo "vdp ... - Make libvdpau_sunxi @bpi and install it to bpi."
    echo "vdp-rdep - Deploy libvdpau-sunxi to packages/bpi via 'rdep -u'."
    echo "pd ... - Make libproxydecoder @bpi and install it to bpi."
    echo "pd-rdep - Deploy libproxydecoder to packages/bpi via 'rdep -u'."
    echo "cedrus [ump] ... - Make libcedrus @bpi and install it to bpi."
    echo "cedrus-rdep - Deploy libcedrus to packages/bpi via 'rdep -u'."
    echo "ump - Rebuild libUMP @bpi and install it to bpi."
    echo "ldp ... - Make ldpreloadhook.so @bpi and intall it to bpi."
    echo "ldp-rdep - Deploy ldpreloadhook.so to packages/bpi via 'rdep -u'."
    echo
    echo "pack-short <output.tgz> - Prepare tar with build results @bpi."
    echo "pack-full <output.tgz> - Prepare tar with complete /opt/networkoptix/ @bpi."
    exit 0
}

#--------------------------------------------------------------------------------------------------
main()
{
    if [ "$#" = "0" -o "$1" = "-h" -o "$1" = "--help" ]; then
        show_help_and_exit
    fi

    if [ "$#" -ge "1" ]; then
        case "$1" in
            #......................................................................................
            "mount")
                sudo umount "$BPI"
                sudo rm -rf "$BPI"
                sudo mkdir -p "$BPI" || exit 1
                sudo chown "$USER" "$BPI"
                sudo mount -o nolock bpi:/ "$BPI"
                exit $?
                ;;
            "sshfs")
                sudo umount "$BPI"
                sudo rm -rf "$BPI"
                sudo mkdir -p "$BPI" || exit 1
                sudo chown "$USER" "$BPI"
                sudo sshfs root@bpi:/ "$BPI" -o nonempty
                exit $?
                ;;
            #......................................................................................
            "copy-scripts")
                copy_scripts
                exit $?
                ;;
            "copy")
                find_vms_dir

                cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

                cp_mediaserver_bins "mediaserver" "mediaserver executable"
                cp_mediaserver_bins "media_db_util" "media_db_util"
                cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
                cp_mediaserver_bins "plugins" "mediaserver plugins"

                copy_scripts

                # Server configuration does not need to be copied.
                #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$MEDIASERVER_DIR" "etc" "$MEDIASERVER_DIR" "etc" "$VMS_DIR"

                cp_lite_client_bins "mobile_client" "mobile_client exe"
                cp_lite_client_bins "video" "Qt OpenGL video plugin"

                # Currently, "copy" verb copies only nx_vms build results.
                #cp_files "$VMS_DIR/../$QT_PATH/lib" "*.so*" "$LIBS_DIR" "Qt libs" "$QT_PATH"
                #cp_mediaserver_bins "vox" "mediaserver vox"
                #
                #cp_lite_client_bins \
                #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,libexec,resources,translations}" \
                #    "mobile_client/bin Qt dirs"
                #cp_sysroot_libs "lib{opus,vpx,webp,webpdemux}.so*" "libs for web-engine"
                #cp_lite_client_bins "ff{mpeg,probe,server}" "ffmpeg executables"
                #cp_libs "ffmpeg" "lib/ffmpeg for proxydecoder"

                exit 0
                ;;
            "copy-s")
                find_vms_dir

                # In case of taking mobile_client from different branch and overriding LIBS_DIR:
                sudo mkdir -p "${BPI}$LIBS_DIR"

                cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

                cp_mediaserver_bins "mediaserver" "mediaserver executable"
                cp_mediaserver_bins "media_db_util" "media_db_util"
                cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
                cp_mediaserver_bins "plugins" "mediaserver plugins"

                copy_scripts

                # Currently, "copy" verb copies only nx_vms build results.
                #cp_files "$VMS_DIR/../$QT_PATH/lib" "*.so*" "$LIBS_DIR" "Qt libs" "$QT_PATH"
                #cp_mediaserver_bins "vox" "mediaserver vox"

                # Server configuration does not need to be copied.
                #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$MEDIASERVER_DIR" "etc" "$MEDIASERVER_DIR" "etc" "$VMS_DIR"

                exit 0
                ;;
            "copy-c")
                find_vms_dir

                cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

                cp_lite_client_bins "mobile_client" "mobile_client exe"

                # Currently, "copy" verb copies only nx_vms build results.
                #cp_files "$VMS_DIR/../$QT_PATH/lib" "*.so*" "$LIBS_DIR" "Qt libs" "$QT_PATH"
                #cp_lite_client_bins \
                #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,video,libexec,resources,translations}" \
                #    "mobile_client/bin Qt dirs"
                #cp_sysroot_libs "lib{opus,vpx,webp,webpdemux}.so*" "libs for web-engine"
                #cp_lite_client_bins "ff{mpeg,probe,server}" "ffmpeg executables"
                #cp_libs "ffmpeg" "lib/ffmpeg for proxydecoder"

                exit 0
                ;;
            "client")
                cp_lite_client_bins "mobile_client" "mobile_client exe"
                exit $?
                ;;
            "server")
                cp_libs "libmediaserver_core.so*" "lib mediaserver_core"
                exit $?
                ;;
            "lib")
                if [ "$2" = "" ]; then
                    find_lib_dir
                    LIB_NAME=$(basename "$LIB_DIR")
                else
                    LIB_NAME="$2"
                fi
                cp_libs "lib$LIB_NAME.so*" "lib $LIB_NAME"
                exit $?
                ;;
            "ini")
                bpi " \
                    touch /tmp/mobile_client.ini && \
                    touch /tmp/nx_media.ini && \
                    touch /tmp/ProxyVideoDecoder.ini && \
                    touch /tmp/proxydecoder.ini
                "
                exit $?
                ;;
            #......................................................................................
            "exec")
                shift
                bpi "$*"
                exit $?
                ;;
            "run")
                shift
                bpi "/opt/networkoptix/mediaserver/var/scripts/start_lite_client $*"
                exit $?
                ;;
            "kill")
                bpi "killall mobile_client"
                exit $?
                ;;
            "start-s")
                shift
                bpi "/etc/init.d/networkoptix-mediaserver start $*"
                exit $?
                ;;
            "stop-s")
                bpi "/etc/init.d/networkoptix-mediaserver stop"
                exit $?
                ;;
            "start-c")
                shift
                bpi "/etc/init.d/networkoptix-lite-client start $*"
                exit $?
                ;;
            "stop-c")
                bpi "/etc/init.d/networkoptix-lite-client stop"
                exit $?
                ;;
            "start")
                shift
                bpi "/etc/init.d/networkoptix-mediaserver start $*"
                echo
                bpi "/etc/init.d/networkoptix-lite-client start $*"
                exit $?
                ;;
            "stop")
                bpi " \
                    /etc/init.d/networkoptix-lite-client stop && \
                    echo && \
                    /etc/init.d/networkoptix-mediaserver stop \
                "
                exit $?
                ;;
            #......................................................................................
            "vdp")
                shift
                bpi "make -C $PACKAGES_SRC_BPI_DIR/libvdpau-sunxi $* && echo SUCCESS"
                exit $?
                ;;
            "vdp-rdep")
                cd "$PACKAGES_DIR/libvdpau-sunxi-1.0${PACKAGE_SUFFIX}" || exit 1
                cp -r "$PACKAGES_SRC_DIR/libvdpau-sunxi"/lib*so* lib/ || exit 1
                rdep -u
                exit $?
                ;;
            "pd")
                shift
                bpi "make -C $PACKAGES_SRC_BPI_DIR/proxy-decoder $* && echo SUCCESS"
                exit $?
                ;;
            "pd-rdep")
                cd "$PACKAGES_DIR/proxy-decoder${PACKAGE_SUFFIX}" || exit 1
                cp -r "$PACKAGES_SRC_DIR/proxy-decoder/libproxydecoder.so" lib/ || exit 1
                cp -r "$PACKAGES_SRC_DIR/proxy-decoder/proxy_decoder.h" include/ || exit 1
                rdep -u
                exit $?
                ;;
            "cedrus")
                shift
                if [ "$1" = "ump" ]; then
                    shift
                    bpi "USE_UMP=1 make -C $PACKAGES_SRC_BPI_DIR/libcedrus $* && echo SUCCESS"
                else
                    bpi "make -C $PACKAGES_SRC_BPI_DIR/libcedrus $* && echo SUCCESS"
                fi
                exit $?
                ;;
            "cedrus-rdep")
                cd "$PACKAGES_DIR/libcedrus-1.0${PACKAGE_SUFFIX}" || exit 1
                cp -r "$PACKAGES_SRC_DIR/libcedrus"/lib*so* lib/ || exit 1
                rdep -u
                exit $?
                ;;
            "ump")
                bpi " \
                    rm -r /tmp/libump && \
                    cp -r $PACKAGES_SRC_BPI_DIR/libump /tmp/ && \
                    cd /tmp/libump && \
                    dpkg-buildpackage -b || echo 'WARNING: Package build failed; manually installing .so and .h.' && \
                    cp -r /tmp/libump/debian/tmp/usr / \
                "
                exit $?
                ;;
            "ldp")
                shift
                bpi "make -C $PACKAGES_SRC_BPI_DIR/ldpreloadhook $* && echo SUCCESS"
                exit $?
                ;;
            "ldp-rdep")
                cd "$PACKAGES_DIR/ldpreloadhook-1.0${PACKAGE_SUFFIX}" || exit 1
                cp -r "$PACKAGES_SRC_DIR/ldpreloadhook"/*.so* lib/ || exit 1
                rdep -u
                exit $?
                ;;
            #......................................................................................
            "pack-short")
                pack_short "$2"
                exit $?
                ;;
            "pack-full")
                pack_full "$2"
                exit $?
                ;;
            #......................................................................................
            *)
                echo "ERROR: Unknown argument: $1"
                exit 1
                ;;
        esac
    else
        echo "ERROR: Invalid arguments. Run with -h for help."
        exit 1
    fi
}

main "$@"
