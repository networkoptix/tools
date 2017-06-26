#!/bin/bash
source "$(dirname "$0")/utils.sh"

nx_load_config "{$CONFIG=".bpi-toolrc"}"
: ${CLIENT_ONLY=""} #< Prohibit non-client commands. Useful for "frankensteins".
: ${SERVER_ONLY=""} #< Prohibit non-server commands. Useful for "frankensteins".
: ${BOX_MNT="/bpi"}
: ${BOX_INITIAL_PASSWORD="admin"}
: ${BOX_PASSWORD="qweasd123"}
: ${BOX_HOST="bpi"} #< Recommented to add "<ip> bpi" to /etc/hosts.
: ${BOX_PORT="22"}
: ${BOX_TERMINAL_TITLE="$BOX_HOST"}
: ${BOX_BACKGROUND_RRGGBB="003000"}
: ${BOX_INSTALL_DIR="/opt/networkoptix"}
: ${BOX_LITE_CLIENT_DIR="$BOX_INSTALL_DIR/lite_client"}
: ${BOX_MEDIASERVER_DIR="$BOX_INSTALL_DIR/mediaserver"}
: ${BOX_LIBS_DIR="$BOX_INSTALL_DIR/lib"}
: ${BOX_DEVELOP_DIR="/root/develop"} #< Mount point at the box for the workstation develop dir.
: ${BOX_PACKAGES_SRC_DIR="$BOX_DEVELOP_DIR/third_party/bpi"} #< Should be mounted at the box.
: ${DEVELOP_DIR="$HOME/develop"}
: ${SDCARD_PARTITION_SECTORS="122879,7043071,81919,"} #< Used to check SD card before accessing it.
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/bpi"} #< Path at the workstation.
: ${PACKAGES_SRC_DIR="$DEVELOP_DIR/third_party/bpi"} #< Path at the workstation.
: ${QT_DIR="$DEVELOP_DIR/buildenv/packages/bpi/qt-5.6.2"} #< Path at the workstation.
: ${BUILD_CONFIG="debug"}
: ${TARGET_IN_VMS_DIR="build_environment/target-bpi"} #< Path component at the workstation.
: ${BUILD_DIR="arm-bpi"} #< Path component at the workstation.
: ${PACKAGE_SUFFIX=""}

#--------------------------------------------------------------------------------------------------

# Constants for working with SD Card via fw_printenv/fw_setenv.
MAC_VAR="ethaddr"
SERIAL_VAR="serial"
FW_CONFIG="/etc/fw_env.config"

# Lines from /etc/network/interfaces at the box.
IP_DHCP_LINE="iface eth0 inet dhcp"
IP_STATIC_LINE="iface eth0 inet static"

LINUX_TOOL="$(dirname "$0")/linux-tool.sh"

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for Banana Pi (Nx1): execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

$(basename "$0") [--verbose] <command>

Here <command> can be one of the following:

nfs # Mount the box root to $BOX_MNT via NFS.
sshfs # Mount the box root to $BOX_MNT via SSHFS.
passwd # Change root password from "$BOX_INITIAL_PASSWORD" to "$BOX_PASSWORD".
mount # Mount ~/develop to the box /root/develop via sshfs. May require workstation password.

sdcard [/dev/sd...] # Read or write SD Card device reference in /etc/fw_env.config and test it.
img [--force] sd_card_image.img # Write the image onto the SD Card.
mac [--force] [xx:xx:xx:xx:xx:xx] # Read or write MAC on an SD Card connected to Linux PC.
serial [--force] [nnnnnnnnn] # Read or write Serial on an SD Card connected to Linux PC.
ip [--force] [<ip-address> <mask> [<gateway>]] # Read/write /etc/network/interfaces on SD Card.
dhcp [--force] # Restore default (configured for DHCP) /etc/network/interfaces on SD Card.

copy # Copy mobile_client and mediaserver libs, bins and scripts to the box $BOX_INSTALL_DIR.
copy-s # Copy mediaserver libs, bins and scripts to the box $BOX_INSTALL_DIR.
copy-c # Copy mobile_client libs and bins to the box $BOX_INSTALL_DIR.
copy-ut # Copy all libs and unit test bins to the box $BOX_INSTALL_DIR.
client # Copy mobile_client exe to the box.
server # Copy mediaserver_core lib to the box.
lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to the box.
ini # Create empty .ini files at the box in /tmp (to be filled with defauls).
install # Install distrib package (.tar.gz) to the box.

ssh [command args] # Execute a command at the box via ssh, or log in to the box via ssh.
run-c [args] # Start mobile_client via "mediaserver/var/scripts/start_lite_client [args]".
kill-c # Stop mobile_client via "killall mobile_client".
start-s [args] # Run mediaserver via "/etc/init.d/networkoptix-mediaserver start [args]".
stop-s # Stop mediaserver via "/etc/init.d/networkoptix-mediaserver stop".
start-c [args] # Run mobile_client via "/etc/init.d/networkoptix-lite-client start [args]".
stop-c # Stop mobile_client via "/etc/init.d/networkoptix-lite-client stop".
run-ut test_name [args] # Run the unit test with strict expectations.
start [args] # Run mediaserver and mobile_client via "/etc/init.d/networkoptix-* start [args]".
stop # Stop mediaserver and mobile_client via "/etc/init.d/networkoptix-* stop".

vdp [args] # Make libvdpau_sunxi at the box and install it to the box, passing [args] to "make".
vdp-rdep # Deploy libvdpau-sunxi to packages/bpi via "rdep -u".
pd [args] # Make libproxydecoder at the box and install it to the box, passing [args] to "make".
pd-rdep # Deploy libproxydecoder to packages/bpi via "rdep -u".
cedrus [ump] [args] # Make libcedrus at the box and install it to the box, passing [args] to "make".
cedrus-rdep # Deploy libcedrus to packages/bpi via "rdep -u".
ump # Rebuild libUMP at the box and install it to the box.
ldp [args] # Make ldpreloadhook.so at the box and intall it to the box, passing [args] to "make".
ldp-rdep # Deploy ldpreloadhook.so to packages/bpi via "rdep -u".

clean # Call "linux-tool.sh clean bpi".
mvn [args] # Call maven with the required platorm and box.
cmake [args] # Call "linux-tool.sh cmake bpi [args]".
gen [args] # Call "linux-tool.sh gen bpi [args]".
build [args] # Call "linux-tool.sh build bpi [args]".
pack-short <output.tgz> # Prepare tar with build results at the box.
pack-full <output.tgz> # Prepare tar with complete /opt/networkoptix/ at the box.
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at the box via ssh, or log in to the box via ssh.
box() # args...
{
    nx_ssh "root" "$BOX_PASSWORD" "$BOX_HOST" "$BOX_PORT" \
        "$BOX_TERMINAL_TITLE" "$BOX_BACKGROUND_RRGGBB" "$@"
}

pack() # archive files...
{
    local ARCHIVE="$1"
    shift
    local FILES=("$@")

    if [ "$ARCHIVE" = "" ]; then
        nx_fail "Archive filename not specified."
    fi

    bpi tar --absolute-names -czvf "$ARCHIVE" "${FILES[@]}"
}

pack_full() # archive
{
    local ARCHIVE="$1"

    pack "$ARCHIVE" \
        "$BOX_INSTALL_DIR" \
        "/etc/init.d/networkoptix*" \
        "/etc/init.d/nx*"
}

# Pack build results and bpi-specific artifacts from third_party.
pack_short()
{
    local ARCHIVE="$1"

    pack "$ARCHIVE" \
        "$BOX_LIBS_DIR"/libappserver2.so \
        "$BOX_LIBS_DIR"/libclient_core.so \
        "$BOX_LIBS_DIR"/libcloud_db_client.so \
        "$BOX_LIBS_DIR"/libcommon.so \
        "$BOX_LIBS_DIR"/libconnection_mediator.so \
        "$BOX_LIBS_DIR"/libmediaserver_core.so \
        "$BOX_LIBS_DIR"/libudt.so \
        "$BOX_LIBS_DIR"/libnx_audio.so \
        "$BOX_LIBS_DIR"/libnx_email.so \
        "$BOX_LIBS_DIR"/libnx_fusion.so \
        "$BOX_LIBS_DIR"/libnx_media.so \
        "$BOX_LIBS_DIR"/libnx_network.so \
        "$BOX_LIBS_DIR"/libnx_streaming.so \
        "$BOX_LIBS_DIR"/libnx_utils.so \
        "$BOX_LIBS_DIR"/libnx_vms_utils.so \
        \
        "$BOX_LIBS_DIR"/ldpreloadhook.so \
        "$BOX_LIBS_DIR"/libcedrus.so \
        "$BOX_LIBS_DIR"/libpixman-1.so \
        "$BOX_LIBS_DIR"/libproxydecoder.so \
        "$BOX_LIBS_DIR"/libvdpau_sunxi.so \
        "$BOX_LIBS_DIR"/libUMP.so \
        \
        "$BOX_LITE_CLIENT_DIR"/bin/mobile_client \
        "$BOX_LITE_CLIENT_DIR"/bin/video/videonode/libnx_bpi_videonode_plugin.so \
        "$BOX_MEDIASERVER_DIR"/bin/mediaserver \
        "$BOX_MEDIASERVER_DIR"/bin/media_db_util \
        "$BOX_MEDIASERVER_DIR"/bin/external.dat \
        "$BOX_MEDIASERVER_DIR"/bin/plugins \
        "/etc/init.d/networkoptix*" \
        "/etc/init.d/nx*" \
        "$BOX_MEDIASERVER_DIR"/var/scripts
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

    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/lib/$BUILD_CONFIG/$MASK" \
        "$BOX_LIBS_DIR" "$DESCRIPTION" "$VMS_DIR"
}

cp_sysroot_libs() # file_mask description
{
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$PACKAGES_DIR/sysroot/usr/lib/arm-linux-gnueabihf/$MASK" \
        "$BOX_LIBS_DIR" "$DESCRIPTION" "packages/bpi/sysroot"
}

cp_lite_client_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/$BUILD_CONFIG/$MASK" \
        "$BOX_LITE_CLIENT_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
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
    cp_scripts_dir "$DIR/bpi/etc/init.d" "${BOX_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/filter-resources/etc/init.d" "${BOX_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/bpi/opt/networkoptix/mediaserver/var/scripts" \
        "${BOX_MNT}$BOX_MEDIASERVER_DIR/var/scripts"
}

# Read SD Card device from /etc/fw_env.config.
read_DEV_SDCARD()
{
    DEV_SDCARD=$(cat "$FW_CONFIG" |awk '{print $1}')
    if [ -z "$DEV_SDCARD" ]; then
        nx_fail "$FW_CONFIG is missing or empty."
    fi
}

# Read SD Card device from /etc/fw_env.config, check that SD Card contains 3 partitions with the
# expected size, umount these partitions.
get_and_check_DEV_SDCARD()
{
    read_DEV_SDCARD

    local PARTITIONS=$(sudo fdisk -l "$DEV_SDCARD" |grep "^$DEV_SDCARD")
    if [ -z "$PARTITIONS" ]; then
        nx_fail "SD Card not found at $DEV_SDCARD (configured in $FW_CONFIG)."
    fi

    local PARTITION_SECTORS=$(awk '{ORS=","; print $3 - $2}' <<<"$PARTITIONS")
    if [ "$PARTITION_SECTORS" != "$SDCARD_PARTITION_SECTORS" ]; then
        nx_fail "SD Card $DEV_SDCARD (configured in $FW_CONFIG) has unexpected partitions."
    fi

    local DEV
    for DEV in $(awk '{print $1}' <<<"$PARTITIONS"); do
        if mount |grep -q "$DEV"; then
            nx_echo "WARNING: $DEV is mounted; unmounting."
            sudo umount "$DEV" || exit $?
        fi
    done
}

force_get_DEV_SDCARD()
{
    read_DEV_SDCARD

    nx_echo "WARNING: $DEV_SDCARD will NOT be checked to be likely an unmounted Nx1 SD Card."
    nx_echo "Your PC HDD can be under risk!"
    read -p "Are you sure to continue? (Y/n) " -n 1 -r
    nx_echo
    if [ "$REPLY" != "Y" ]; then
        nx_fail "Aborted, no changes made."
    fi
}

fw_print() # var output_prefix
{
    local VAR="$1"
    local OUTPUT_PREFIX="$2"

    local ENV
    ENV=$(sudo fw_printenv) || exit $?
    rm -rf fw_printenv.lock

    local VALUE=$(echo "$ENV" |grep "$VAR=" |sed "s/$VAR=//g")
    nx_echo "$OUTPUT_PREFIX$VALUE"
}

fw_set() # var value
{
    local VAR="$1"
    local VALUE="$2"

    sudo fw_setenv "$VAR" "$VALUE" || exit $?
    rm -rf fw_printenv.lock
    sync || exit $?
}

check_mac() # mac
{
    local MAC="$1"

    local HEX="[0-9A-Fa-f][0-9A-Fa-f]"
    local MAC_REGEX="^$HEX:$HEX:$HEX:$HEX:$HEX:$HEX$"
    if [[ ! $MAC =~ $MAC_REGEX ]]; then
        nx_fail "Invalid MAC: $MAC"
    fi
}

check_serial() # serial
{
    local SERIAL="$1"

    local SERIAL_REGEX="^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$"
    if [[ ! $SERIAL =~ $SERIAL_REGEX ]]; then
        nx_fail "Invalid Serial: $SERIAL"
    fi

    if [ ${SERIAL:0:2} -gt 31 ]; then
        nx_fail "Invalid Serial: first pair of digits should be <= 31."
    fi
    if [ ${SERIAL:2:2} -gt 12 ]; then
        nx_fail "Invalid Serial: second pair of digits should be <= 12."
    fi
}

# [in] DEV_SDCARD Device representing the whole SD Card.
# [out] SD_DIR Directory to which the SD Card is mounted.
sd_card_mount_SD_DIR()
{
    SD_DIR=$(mktemp -d) || exit $?
    sudo mount -t ext4 -o rw,nosuid,nodev,uhelper=udisks2 "${DEV_SDCARD}2" "$SD_DIR" || exit $?
}

# [in] SD_DIR Directory to which the SD Card is mounted.
sd_card_umount_SD_DIR()
{
    sudo umount "$SD_DIR" || exit $?
    rmdir "$SD_DIR" || exit $?
}

get_value_by_prefix() # /etc/network/interfaces prefix
{
    local FILE="$1"
    local PREFIX="$2"
    grep "^\\s*$PREFIX " "$FILE" |sed "s/\\s*$PREFIX //"
}

is_line_present() # /etc/network/interfaces line_text
{
    local FILE="$1"
    local LINE="$2"
    grep -q "^\\s*$LINE\\s*$" "$FILE"
}

comment_out_line()  # /etc/network/interfaces line_text
{
    local FILE="$1"
    local LINE="$2"
    sudo sed --in-place "s/^\\(\\s*$LINE\\s*\\)/#\\1/" "$FILE"

    nx_log_file_contents "$FILE"
}

# If the prefix is found, uncomment if commented out, and change the value. Otherwise, add a line.
set_value_by_prefix() #  # /etc/network/interfaces prefix value
{
    local FILE="$1"
    local PREFIX="$2"
    local VALUE="$3"

    if ! is_line_present "$FILE" "#\\?\\s*$PREFIX.*"; then
        echo "$PREFIX" "$VALUE" |sudo tee -a "$FILE" >/dev/null || exit $?
    else
        # Uncomment the line (if commented out), and change the value.
        sudo sed --in-place "s/^\\(\\s*\\)#\\?\\(\\s*\\)$PREFIX.*/\\1\\2$PREFIX $VALUE/" "$FILE" \
            || exit $?
    fi

    nx_log_file_contents "$FILE"
}

ip_show() # /etc/network/interfaces
{
    local FILE="$1"

    nx_log_file_contents "$FILE"

    if is_line_present "$FILE" "$IP_DHCP_LINE"; then
        if is_line_present "$FILE" "$IP_STATIC_LINE"; then
            nx_fail "IP config unrecognized: both 'static' and 'dhcp' lines are found in $FILE"
        fi
        nx_echo "$IP_DHCP_LINE"
    else
        if ! is_line_present "$FILE" "$IP_STATIC_LINE"; then
            nx_fail "IP config unrecognized: none of 'static' and 'dhcp' lines are found in $FILE"
        fi

        local IP_ADDRESS=$(get_value_by_prefix "$FILE" "address")
        if [ -z "$IP_ADDRESS" ]; then
            nx_fail "IP address not found in $FILE"
        fi

        local IP_NETMASK=$(get_value_by_prefix "$FILE" "netmask")
        if [ -z "$IP_NETMASK" ]; then
            nx_fail "IP netmask not found in $FILE"
        fi

        local IP_GATEWAY=$(get_value_by_prefix "$FILE" "gateway")

        nx_echo "$IP_STATIC_LINE"
        nx_echo -e "\t""address $IP_ADDRESS"
        nx_echo -e "\t""netmask $IP_NETMASK"
        if [ ! -z "$IP_GATEWAY" ]; then
            nx_echo -e "\t""gateway $IP_GATEWAY"
        fi
    fi
}

ip_set_static() # /etc/network/interfaces ip_address netmask [gateway]
{
    local FILE="$1"
    local IP_ADDRESS="$2"
    local IP_NETMASK="$3"
    local IP_GATEWAY="$4" #< Can be empty

    if [ -z "$IP_NETMASK" ]; then
        nx_fail "IP netmask should be specified."
    fi

    nx_echo "Old IP config:"
    ip_show "$FILE"
    nx_echo

    comment_out_line "$FILE" "$IP_DHCP_LINE" || exit $?
    set_value_by_prefix "$FILE" "$IP_STATIC_LINE" "" || exit $?
    set_value_by_prefix "$FILE" "address" "$IP_ADDRESS" || exit $?
    set_value_by_prefix "$FILE" "netmask" "$IP_NETMASK" || exit $?
    if [ ! -z "$IP_GATEWAY" ]; then
        set_value_by_prefix "$FILE" "gateway" "$IP_GATEWAY"
    else
        comment_out_line "$FILE" "gateway .*" || exit $?
    fi

    nx_echo "New IP config:"
    ip_show "$FILE"
}

ip_set_dhcp() # /etc/network/interfaces
{
    local FILE="$1"

    cat <<EOF |sudo tee "$FILE" >/dev/null
# interfaces(5) file used by ifup(8) and ifdown(8)
auto lo
iface lo inet loopback

auto eth0

# dhcp configuration
iface eth0 inet dhcp

# static ip configuration
#iface eth0 inet static
#address 192.168.0.103
#netmask 255.255.254.0
#gateway 192.168.0.101
EOF
}

do_mvn() # "$@"
{
    mvn -Dbox=bpi -Darch=arm "$@"
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
        sshfs)
            fusermount -u "$BOX_MNT" 2>/dev/null
            sudo rm -rf "$BOX_MNT" || exit $?
            sudo mkdir -p "$BOX_MNT" || exit $?
            sudo chown "$USER" "$BOX_MNT"

            echo "$BOX_PASSWORD" |( \
                sshfs root@"$BOX_HOST":/ "$BOX_MNT" \
                    -o UserKnownHostsFile=/dev/null,StrictHostKeyChecking=no \
                    -o nonempty,password_stdin && \
                        echo "Box mounted via sshfs to $BOX_MNT" )
            ;;
        passwd)
            sshpass -p "$BOX_INITIAL_PASSWORD" ssh -t "root@$BOX_HOST" \
                "(echo \"$BOX_PASSWORD\"; echo \"$BOX_PASSWORD\") |passwd" \
                || exit $?
            nx_echo "Old box password: $BOX_INITIAL_PASSWORD"
            nx_echo "New box password: $BOX_PASSWORD"
            ;;
        mount)
            local BOX_IP=$(ping -q -c 1 -t 1 $BOX_HOST | grep PING | sed -e "s/).*//" | sed -e "s/.*(//")
            local SUBNET=$(echo "$BOX_IP" |awk 'BEGIN { FS = "." }; { print $1 "." $2 }')
            local SELF_IP=$(ifconfig |awk '/inet addr/{print substr($2,6)}' |grep "$SUBNET")
            box umount "$BOX_DEVELOP_DIR" #< Just in case.
            box mkdir -p "$BOX_DEVELOP_DIR" || exit $?
            box apt-get install -y sshfs #< Install sshfs.

            # TODO: Fix: "sshfs" does not work via sshpass, but works if executed directly at the box.
            nx_echo
            nx_echo "ATTENTION: Now execute the following command directly at the box:"
            echo sshfs "$USER@$SELF_IP:$DEVELOP_DIR" "$BOX_DEVELOP_DIR" -o nonempty
            #box sshfs "$USER@$SELF_IP:$DEVELOP_DIR" "$BOX_DEVELOP_DIR" -o nonempty \
                #&& echo "$DEVELOP_DIR mounted to the box $BOX_DEVELOP_DIR."
            ;;
        #..........................................................................................
        sdcard) # [/dev/sd...]
            local NEW_DEV_SDCARD="$1"
            read_DEV_SDCARD
            if [ -z "$NEW_DEV_SDCARD" ]; then
                nx_echo "SD Card device: $DEV_SDCARD"
            else
                nx_echo "Old SD Card device: $DEV_SDCARD"
                local NEW_CONFIG=$(cat "$FW_CONFIG" |sed "s#$DEV_SDCARD#$NEW_DEV_SDCARD#")
                echo "$NEW_CONFIG" |sudo tee "$FW_CONFIG" >/dev/null || exit $?
                read_DEV_SDCARD
                if [ "$DEV_SDCARD" != "$NEW_DEV_SDCARD" ]; then
                    nx_fail "Wrong SD Card device in $FW_CONFIG: $DEV_SDCARD" $'\n'"$NEW_CONFIG"
                fi
                nx_echo "New SD Card device: $DEV_SDCARD"
            fi
            get_and_check_DEV_SDCARD
            nx_echo "Seems to contain expected Nx1 partitions, not mounted."
            ;;
        img) # [--force] sd_card_image.img
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi
            local IMG="$1"
            if [ -z "$IMG" ]; then
                nx_fail "Image file not specified."
            fi
            local IMG_SIZE=$(du -h "$IMG" |sed 's/\t.*//')
            nx_echo "Writing to $DEV_SDCARD: $IMG_SIZE $IMG"
            nx_sudo_dd if="$IMG" of="$DEV_SDCARD" bs=1M || exit $?
            nx_echo "Performing sync..."
            sync || exit $?
            nx_echo "Done"
            ;;
        mac) # [--force] [xx:xx:xx:xx:xx:xx]
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi
            local MAC="$1"
            if [ -z "$MAC" ]; then
                fw_print "$MAC_VAR" || exit $?
            else
                fw_print "$MAC_VAR" "Old MAC: " || exit $?
                check_mac "$MAC" || exit $?
                fw_set "$MAC_VAR" "$MAC"
                fw_print "$MAC_VAR" "New MAC: " || exit $?
            fi
            ;;
        serial) # [--force] [nnnnnnnnn]
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi
            local SERIAL="$1"
            if [ -z "$SERIAL" ]; then
                fw_print "$SERIAL_VAR" || exit $?
            else
                fw_print "$SERIAL_VAR" "Old Serial: " || exit $?
                check_serial "$SERIAL" || exit $?
                fw_set "$SERIAL_VAR" "$SERIAL" || exit $?
                fw_print "$SERIAL_VAR" "New Serial: " || exit $?
            fi
            ;;
        ip) # [--force] [<ip-address> <mask> [<gateway>]]
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi

            sd_card_mount_SD_DIR
            local FILE="$SD_DIR/etc/network/interfaces"

            # Subshell used to finally umount.
            (
                if [ -z "$1" ]; then
                    ip_show "$FILE"
                else
                    ip_set_static "$FILE" "$@"
                fi
            )
            local RESULT=$?
            sd_card_umount_SD_DIR
            exit $RESULT
            ;;
        dhcp) # [--force]
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi

            sd_card_mount_SD_DIR
            local FILE="$SD_DIR/etc/network/interfaces"

            # Subshell used to finally umount.
            (
                ip_set_dhcp "$FILE"
            )
            local RESULT=$?
            sd_card_umount_SD_DIR
            exit $RESULT
            ;;
        #..........................................................................................
        copy-scripts)
            copy_scripts
            ;;
        copy)
            assert_not_client_only
            assert_not_server_only
            find_VMS_DIR

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "media_db_util" "media_db_util"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            copy_scripts

            # Server configuration does not need to be copied.
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$BOX_MEDIASERVER_DIR/etc" "$BOX_MEDIASERVER_DIR" "etc" "$VMS_DIR"

            cp_lite_client_bins "mobile_client" "mobile_client exe"
            cp_lite_client_bins "video" "Qt OpenGL video plugin"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_DIR/lib/*.so*" "$BOX_LIBS_DIR" "Qt libs" "$QT_DIR"
            #cp_mediaserver_bins "vox" "mediaserver vox"
            #
            #cp_lite_client_bins \
            #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,libexec,resources,translations}" \
            #    "mobile_client/bin Qt dirs"
            #cp_sysroot_libs "lib{opus,vpx,webp,webpdemux}.so*" "libs for web-engine"
            #cp_lite_client_bins "ff{mpeg,probe,server}" "ffmpeg executables"
            #cp_libs "ffmpeg" "lib/ffmpeg for proxydecoder"
            ;;
        copy-s)
            assert_not_client_only
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
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$BOX_MEDIASERVER_DIR/etc" "$BOX_MEDIASERVER_DIR" "etc" "$VMS_DIR"
            ;;
        copy-c)
            assert_not_server_only
            find_VMS_DIR

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_lite_client_bins "mobile_client" "mobile_client exe"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_DIR/lib/*.so*" "$BOX_LIBS_DIR" "Qt libs" "$QT_DIR"
            #cp_lite_client_bins \
            #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,video,libexec,resources,translations}" \
            #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,video,libexec,resources,translations}" \
            #    "mobile_client/bin Qt dirs"
            #cp_sysroot_libs "lib{opus,vpx,webp,webpdemux}.so*" "libs for web-engine"
            #cp_lite_client_bins "ff{mpeg,probe,server}" "ffmpeg executables"
            #cp_libs "ffmpeg" "lib/ffmpeg for proxydecoder"
            ;;
        copy-ut)
            find_VMS_DIR
            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"
            cp_files "$VMS_DIR/$TARGET_IN_VMS_DIR/bin/$BUILD_CONFIG/*_ut" \
                "$BOX_MEDIASERVER_DIR/ut" "unit tests" "$VMS_DIR"
            ;;
        client)
            assert_not_server_only
            cp_lite_client_bins "mobile_client" "mobile_client exe"
            ;;
        server)
            assert_not_client_only
            cp_libs "libmediaserver_core.so*" "lib mediaserver_core"
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
                touch /tmp/nx_media.ini "[&&]" \
                touch /tmp/ProxyVideoDecoder.ini "[&&]" \
                touch /tmp/proxydecoder.ini
            ;;
        install)
            find_VMS_DIR
            box tar xfzv \
                "$BOX_DEVELOP_DIR/${VMS_DIR#$DEVELOP_DIR}/edge_firmware/rpi/target-bpi/*.tar.gz" \
                -C "/"
            ;;
        #..........................................................................................
        ssh)
            box "$@"
            ;;
        run-c)
            box /opt/networkoptix/mediaserver/var/scripts/start_lite_client "$@"
            ;;
        kill-c)
            box killall mobile_client
            ;;
        start-s)
            box /etc/init.d/networkoptix-mediaserver start "$@"
            ;;
        stop-s)
            box /etc/init.d/networkoptix-mediaserver stop
            ;;
        start-c)
            box /etc/init.d/networkoptix-lite-client start "$@"
            ;;
        stop-c)
            box /etc/init.d/networkoptix-lite-client stop
            ;;
        start)
            box \
                /etc/init.d/networkoptix-mediaserver start "$@" "[&&]" \
                echo "[&&]" \
                /etc/init.d/networkoptix-lite-client start "$@"
            ;;
        stop)
            box \
                /etc/init.d/networkoptix-lite-client stop "[&&]" \
                echo "[&&]" \
                /etc/init.d/networkoptix-mediaserver stop
            ;;
        run-ut)
            local TEST_NAME="$1"; shift
            [ -z "$TEST_NAME" ] && fail "Test name not specified."
            nx_echo "Running: $TEST_NAME $@"
            box LD_LIBRARY_PATH="$BOX_LIBS_DIR" \
                "$BOX_MEDIASERVER_DIR/ut/$TEST_NAME" "$@"
            ;;
        #..........................................................................................
        vdp)
            box make -C "$BOX_PACKAGES_SRC_DIR/libvdpau-sunxi" "$@" "[&&]" echo "SUCCESS"
            ;;
        vdp-rdep)
            cd "$PACKAGES_DIR/libvdpau-sunxi-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/libvdpau-sunxi"/lib*so* lib/ || exit $?
            rdep -u
            ;;
        pd)
            box make -C "$BOX_PACKAGES_SRC_DIR/proxy-decoder" "$@" "[&&]" echo "SUCCESS"
            ;;
        pd-rdep)
            cd "$PACKAGES_DIR/proxy-decoder${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/proxy-decoder/libproxydecoder.so" lib/ || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/proxy-decoder/proxy_decoder.h" include/ || exit $?
            rdep -u
            ;;
        cedrus)
            if [ "$1" = "ump" ]; then
                shift
                box USE_UMP=1 make -C "$BOX_PACKAGES_SRC_DIR/libcedrus" "$@" "[&&]" echo "SUCCESS"
            else
                box make -C "$BOX_PACKAGES_SRC_DIR/libcedrus" "$@" "[&&]" echo "SUCCESS"
            fi
            ;;
        cedrus-rdep)
            cd "$PACKAGES_DIR/libcedrus-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/libcedrus"/lib*so* lib/ || exit $?
            rdep -u
            ;;
        ump)
            box \
                rm -r /tmp/libump "[&&]" \
                cp -r "$BOX_PACKAGES_SRC_DIR/libump" /tmp/ "[&&]" \
                cd /tmp/libump "[&&]" \
                "[{]" dpkg-buildpackage -b "[||]" \
                    echo "WARNING: Package build failed; manually installing .so and .h." "[}]" "[;]" \
                cp -r /tmp/libump/debian/tmp/usr /
            ;;
        ldp)
            box make -C "$BOX_PACKAGES_SRC_DIR/ldpreloadhook" "$@" "[&&]" echo "SUCCESS"
            ;;
        ldp-rdep)
            cd "$PACKAGES_DIR/ldpreloadhook-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_sync "$PACKAGES_SRC_DIR/ldpreloadhook"/*.so* lib/ || exit
            rdep -u
            ;;
        #..........................................................................................
        clean)
            "$LINUX_TOOL" clean bpi "$@"
            ;;
        mvn)
            do_mvn "$@"
            ;;
        cmake)
            "$LINUX_TOOL" cmake bpi "$@"
            ;;
        gen)
            "$LINUX_TOOL" gen bpi "$@"
            ;;
        build)
            "$LINUX_TOOL" build bpi "$@"
            ;;
        pack-short)
            pack_short "$1"
            ;;
        pack-full)
            pack_full "$1"
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
