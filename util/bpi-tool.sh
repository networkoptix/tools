#!/bin/bash
source "$(dirname $0)/utils.sh"

# Collection of various convenient commands used for Banana Pi (Nx1) development.

#--------------------------------------------------------------------------------------------------
# Configuration

nx_load_config "bpirc"
: ${BPI_MNT:="/bpi"}
: ${BPI_INITIAL_PASSWORD:="admin"}
: ${BPI_PASSWORD:="qweasd123"}
: ${BPI_HOST:="bpi"} #< Recommented to add "<ip> bpi" to /etc/hosts.
: ${BPI_TERMINAL_TITLE:="$BPI_HOST"}
: ${BPI_BACKGROUND_RRGGBB="003000"}
: ${BPI_PACKAGES_SRC_DIR="/root/develop/third_party/bpi"} #< Should be mounted at bpi.

# Lines from /etc/network/interfaces at bpi.
IP_DHCP_LINE="iface eth0 inet dhcp"
IP_STATIC_LINE="iface eth0 inet static"

# Paths at workstation.
DEVELOP_DIR="$HOME/develop"
PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/bpi"
PACKAGES_SRC_DIR="DEVELOP_DIR/third_party/bpi"
QT_PATH="$DEVELOP_DIR/buildenv/packages/bpi/qt-5.6.2"

# Paths at bpi.
BPI_INSTALL_DIR="/opt/networkoptix"
BPI_LITE_CLIENT_DIR="$BPI_INSTALL_DIR/lite_client"
BPI_MEDIASERVER_DIR="$BPI_INSTALL_DIR/mediaserver"

# BPI_LIBS_DIR can be predefined.
if [ -z "$BPI_LIBS_DIR" ]; then
    BPI_LIBS_DIR="$BPI_INSTALL_DIR/lib"
else
    nx_echo "ATTENTION: BPI_LIBS_DIR overridden to $BPI_LIBS_DIR"
    BPI_LIBS_DIR_OVERRIDEN=1
fi

# PACKAGE_SUFFIX can be predefined.
if [ -z "$PACKAGE_SUFFIX" ]; then
    PACKAGE_SUFFIX=
else
    nx_echo "ATTENTION: PACKAGE_SUFFIX defined as $PACKAGE_SUFFIX"
fi

# Constants for working with SD Card via fw_printenv/fw_setenv.
MAC_VAR="ethaddr"
SERIAL_VAR="serial"
FW_CONFIG="/etc/fw_env.config"
SDCARD_PARTITION_SIZES="61440,3521536,40960,"

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for Banana Pi (NX1): execute various commands.
Use ~/.bpirc to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:
$(basename $0) [--verbose] <command>
Here <command> can be one of the following:

nfs # Mount bpi root to $BPI_MNT via NFS.
sshfs # Mount bpi root to $BPI_MNT via SSHFS.
passwd # Change root password from "$BPI_INITIAL_PASSWORD" to "$BPI_PASSWORD".

sdcard [/dev/sd...] # Read or write SD Card device reference in /etc/fw_env.config and test it.
img [--force] sd_card_image.img # Write the image onto the SD Card.
mac [--force] [xx:xx:xx:xx:xx:xx] # Read or write MAC on an SD Card connected to Linux PC.
serial [--force] [nnnnnnnnn] # Read or write Serial on an SD Card connected to Linux PC.
ip [--force] [<ip-address> <mask> [<gateway>]] # Read/write /etc/network/interfaces on SD Card.
dhcp [--force] # Restore default (configured for DHCP) /etc/network/interfaces on SD Card.

copy # Copy mobile_client and mediaserver libs, bins and scripts to bpi $BPI_INSTALL_DIR.
copy-s # Copy mediaserver libs, bins and scripts to bpi $BPI_INSTALL_DIR.
copy-c # Copy mobile_client libs and bins to bpi $BPI_INSTALL_DIR.
copy-ut # Copy all libs and unit test bins to bpi $BPI_INSTALL_DIR.
client # Copy mobile_client exe to bpi.
server # Copy mediaserver_core lib to bpi.
common # Copy common lib to bpi.
lib [<name>] # Copy the specified (or pwd-guessed common_libs/<name>) library to bpi.
ini # Create empty .ini files @bpi in /tmp (to be filled with defauls).

ssh [command args] # Execute a command at bpi via ssh, or log in to bpi via ssh.
run-c [args] # Start mobile_client via "mediaserver/var/scripts/start_lite_client [args]".
kill-c # Stop mobile_client via "killall mobile_client".
start-s [args] # Run mediaserver via "/etc/init.d/networkoptix-mediaserver start [args]".
stop-s # Stop mediaserver via "/etc/init.d/networkoptix-mediaserver stop".
start-c [args] # Run mobile_client via "/etc/init.d/networkoptix-lite-client start [args]".
stop-s # Stop mobile_client via "/etc/init.d/networkoptix-lite-client stop".
run-ut [test-name args] # Run the specified unit test with strict expectations.
start [args] # Run mediaserver and mobile_client via "/etc/init.d/networkoptix-* start [args]".
stop # Stop mediaserver and mobile_client via "/etc/init.d/networkoptix-* stop".

vdp [args] # Make libvdpau_sunxi at bpi and install it to bpi, passing [args] to "make".
vdp-rdep # Deploy libvdpau-sunxi to packages/bpi via "rdep -u".
pd [args] # Make libproxydecoder at bpi and install it to bpi, passing [args] to "make".
pd-rdep # Deploy libproxydecoder to packages/bpi via "rdep -u".
cedrus [ump] [args] # Make libcedrus at bpi and install it to bpi, passing [args] to "make".
cedrus-rdep # Deploy libcedrus to packages/bpi via "rdep -u".
ump # Rebuild libUMP at bpi and install it to bpi.
ldp [args] # Make ldpreloadhook.so at bpi and intall it to bpi, passing [args] to "make".
ldp-rdep # Deploy ldpreloadhook.so to packages/bpi via "rdep -u".

rebuild [args] # Perform "mvn clean package <required-args> [args]".
pack-short <output.tgz> # Prepare tar with build results at bpi.
pack-full <output.tgz> # Prepare tar with complete /opt/networkoptix/ at bpi.
EOF
}

#--------------------------------------------------------------------------------------------------

# Execute a command at bpi via ssh, or log in to bpi via ssh.
bpi() # args...
{
    # Ssh reparses the combined args string at bpi, thus, it needs to be escaped.
    local ARGS=
    if [ ! -z "$*" ]; then
        printf -v ARGS "%q " "$@"
        ARGS="${ARGS//\\\*/*}" #< Unescape each "*" to enable passing globs.
        ARGS="${ARGS%?}" #< Trim the last space introduced by printf.
    fi    

    local OLD_BACKGROUND
    nx_get_background OLD_BACKGROUND
    nx_set_background "$BPI_BACKGROUND_RRGGBB"
    nx_push_title
    nx_set_title "$BPI_TERMINAL_TITLE"

    sshpass -p "$BPI_PASSWORD" ssh -t "root@$BPI_HOST" ${ARGS:+"$ARGS"} #< Omit the param if empty.

    nx_pop_title
    nx_set_background "$OLD_BACKGROUND"
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
        "$BPI_INSTALL_DIR" \
        "/etc/init.d/networkoptix*" \
        "/etc/init.d/nx*"
}

# Pack build results and bpi-specific artifacts from third_party.
pack_short()
{
    local ARCHIVE="$1"

    pack "$ARCHIVE" \
        "$BPI_LIBS_DIR"/libappserver2.so \
        "$BPI_LIBS_DIR"/libclient_core.so \
        "$BPI_LIBS_DIR"/libcloud_db_client.so \
        "$BPI_LIBS_DIR"/libcommon.so \
        "$BPI_LIBS_DIR"/libconnection_mediator.so \
        "$BPI_LIBS_DIR"/libmediaserver_core.so \
        "$BPI_LIBS_DIR"/libudt.so \
        "$BPI_LIBS_DIR"/libnx_audio.so \
        "$BPI_LIBS_DIR"/libnx_email.so \
        "$BPI_LIBS_DIR"/libnx_fusion.so \
        "$BPI_LIBS_DIR"/libnx_media.so \
        "$BPI_LIBS_DIR"/libnx_network.so \
        "$BPI_LIBS_DIR"/libnx_streaming.so \
        "$BPI_LIBS_DIR"/libnx_utils.so \
        "$BPI_LIBS_DIR"/libnx_vms_utils.so \
        \
        "$BPI_LIBS_DIR"/ldpreloadhook.so \
        "$BPI_LIBS_DIR"/libcedrus.so \
        "$BPI_LIBS_DIR"/libpixman-1.so \
        "$BPI_LIBS_DIR"/libproxydecoder.so \
        "$BPI_LIBS_DIR"/libvdpau_sunxi.so \
        "$BPI_LIBS_DIR"/libUMP.so \
        \
        "$BPI_LITE_CLIENT_DIR"/bin/mobile_client \
        "$BPI_LITE_CLIENT_DIR"/bin/video/videonode/libnx_bpi_videonode_plugin.so \
        "$BPI_MEDIASERVER_DIR"/bin/mediaserver \
        "$BPI_MEDIASERVER_DIR"/bin/media_db_util \
        "$BPI_MEDIASERVER_DIR"/bin/external.dat \
        "$BPI_MEDIASERVER_DIR"/bin/plugins \
        "/etc/init.d/networkoptix*" \
        "/etc/init.d/nx*" \
        "$BPI_MEDIASERVER_DIR"/var/scripts
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

cp_files()
{
    local FILES_SRC="$1"
    local FILES_LIST="$2"
    local FILES_DST="$3"
    local FILES_DESCRIPTION="$4"
    local FILES_SRC_DESCRIPTION="$5"

    nx_echo "Copying $FILES_DESCRIPTION from $FILES_SRC_DESCRIPTION to $FILES_DST/"

    mkdir -p "${BPI_MNT}$FILES_DST" || exit $?

    # Here eval performs expanding of globs, including "{,}".
    FILES_LIST_EXPANDED=$(eval echo "$FILES_SRC/$FILES_LIST")

    nx_rsync $FILES_LIST_EXPANDED "${BPI_MNT}$FILES_DST/" || exit $?
}

cp_libs() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/build_environment/target-bpi/lib/debug" "$MASK" \
        "$BPI_LIBS_DIR" "$DESCRIPTION" "$VMS_DIR"
}

cp_sysroot_libs() # file_mask description
{
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$PACKAGES_DIR/sysroot/usr/lib/arm-linux-gnueabihf" "$MASK" \
        "$BPI_LIBS_DIR" "$DESCRIPTION" "packages/bpi/sysroot"
}

cp_lite_client_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/build_environment/target-bpi/bin/debug" "$MASK" \
        "$BPI_LITE_CLIENT_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
}

cp_mediaserver_bins() # file_mask description
{
    find_VMS_DIR
    local MASK="$1"
    local DESCRIPTION="$2"
    cp_files "$VMS_DIR/build_environment/target-bpi/bin/debug" "$MASK" \
        "$BPI_MEDIASERVER_DIR/bin" "$DESCRIPTION" "$VMS_DIR"
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
    cp_scripts_dir "$DIR/bpi/etc/init.d" "${BPI_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/filter-resources/etc/init.d" "${BPI_MNT}/etc/init.d"
    cp_scripts_dir "$DIR/bpi/opt/networkoptix/mediaserver/var/scripts" \
        "${BPI_MNT}$BPI_MEDIASERVER_DIR/var/scripts"
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

    local PARTITION_SIZES=$(awk '{ORS=","; print $4}' <<<"$PARTITIONS")
    if [ "$PARTITION_SIZES" != "$SDCARD_PARTITION_SIZES" ]; then
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

    log_file_contents "$FILE"
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

    log_file_contents "$FILE"
}

ip_show() # /etc/network/interfaces
{
    local FILE="$1"

    log_file_contents "$FILE"

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

ip_write_IP_ADDRESS_and_IP_NETMASK_and_IP_GATEWAY() # /etc/network/interfaces
{
    local FILE="$1"

    comment_out_line "$FILE" "$IP_DHCP_LINE" || exit $?

    set_value_by_prefix "$FILE" "$IP_STATIC_LINE" "" || exit $?

    set_value_by_prefix "$FILE" "address" "$IP_ADDRESS" || exit $?
    set_value_by_prefix "$FILE" "netmask" "$IP_NETMASK" || exit $?

    if [ ! -z "$IP_GATEWAY" ]; then
        set_value_by_prefix "$FILE" "gateway" "$IP_GATEWAY"
    else
        comment_out_line "$FILE" "gateway .*" || exit $?
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

show_or_set_ip_config() # /etc/network/interfaces [<ip-address> <mask> [<gateway>]]
{
    local FILE="$1"
    shift

    if [ -z "$1" ]; then
        ip_show "$FILE"
    else
        local IP_ADDRESS="$1"
        local IP_NETMASK="$2"
        if [ -z "$IP_NETMASK" ]; then
            nx_fail "IP netmask should be specified."
        fi
        local IP_GATEWAY="$3" #< Can be empty
        if [ ! -z "$4" ]; then
            nx_fail "Too many arguments."
        fi

        nx_echo "Old IP config:"
        ip_show "$FILE"
        nx_echo

        ip_write_IP_ADDRESS_and_IP_NETMASK_and_IP_GATEWAY "$FILE"

        nx_echo "New IP config:"
        ip_show "$FILE"
    fi
}

set_default_ip_config() # /etc/network/interfaces
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

#--------------------------------------------------------------------------------------------------

main()
{
    case "$1" in
        nfs)
            sudo umount "$BPI_MNT"
            sudo rm -rf "$BPI_MNT" || exit $?
            sudo mkdir -p "$BPI_MNT" || exit $?
            sudo chown "$USER" "$BPI_MNT"

            sudo mount -o nolock bpi:/ "$BPI_MNT"
            exit $?
            ;;
        sshfs)
            sudo umount "$BPI_MNT"
            sudo rm -rf "$BPI_MNT" || exit $?
            sudo mkdir -p "$BPI_MNT" || exit $?
            sudo chown "$USER" "$BPI_MNT"
            
            echo "$BPI_PASSWORD" |sshfs root@"$BPI_HOST":/ "$BPI_MNT" -o nonempty,password_stdin
            exit $?
            ;;
        passwd)
            sshpass -p "$BPI_INITIAL_PASSWORD" ssh -t "root@$BPI_HOST" \
                "(echo \"$BPI_PASSWORD\"; echo \"$BPI_PASSWORD\") |passwd" \
                || exit $?
            nx_echo "Old bpi password: $BPI_INITIAL_PASSWORD"
            nx_echo "New bpi password: $BPI_PASSWORD"
            exit $?
            ;;
        #..........................................................................................
        sdcard) # [/dev/sd...]
            shift
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
            exit $?
            ;;
        img) # [--force] sd_card_image.img
            shift
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
            exit $?
            ;;
        mac) # [--force] [xx:xx:xx:xx:xx:xx]
            shift
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
            exit $?
            ;;
        serial) # [--force] [nnnnnnnnn]
            shift
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
            exit $?
            ;;
        ip) # [--force] [<ip-address> <mask> [<gateway>]]
            shift
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi

            sd_card_mount_SD_DIR
            local FILE="$SD_DIR/etc/network/interfaces"

            (show_or_set_ip_config "$FILE" "$@") #< Subshell allows to umount on error.
            local RESULT=$?
            sd_card_umount_SD_DIR
            exit $RESULT
            ;;
        dhcp) # [--force]
            shift
            if [ "$1" = "--force" ]; then
                shift
                force_get_DEV_SDCARD
            else
                get_and_check_DEV_SDCARD
            fi

            sd_card_mount_SD_DIR
            local FILE="$SD_DIR/etc/network/interfaces"

            (set_default_ip_config "$FILE") #< Subshell allows to umount on error.
            local RESULT=$?
            sd_card_umount_SD_DIR
            exit $RESULT
            ;;
        #..........................................................................................
        copy-scripts)
            copy_scripts
            exit $?
            ;;
        copy)
            find_VMS_DIR

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "media_db_util" "media_db_util"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            copy_scripts

            # Server configuration does not need to be copied.
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$BPI_MEDIASERVER_DIR" "etc" "$BPI_MEDIASERVER_DIR" "etc" "$VMS_DIR"

            cp_lite_client_bins "mobile_client" "mobile_client exe"
            cp_lite_client_bins "video" "Qt OpenGL video plugin"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_PATH/lib" "*.so*" "$BPI_LIBS_DIR" "Qt libs" "$QT_PATH"
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
        copy-s)
            find_VMS_DIR

            # In case of taking mobile_client from different branch and overriding BPI_LIBS_DIR:
            mkdir -p "${BPI_MNT}$BPI_LIBS_DIR"

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_mediaserver_bins "mediaserver" "mediaserver executable"
            cp_mediaserver_bins "media_db_util" "media_db_util"
            cp_mediaserver_bins "external.dat" "web-admin (external.dat)"
            cp_mediaserver_bins "plugins" "mediaserver plugins"

            copy_scripts

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_PATH/lib" "*.so*" "$BPI_LIBS_DIR" "Qt libs" "$QT_PATH"
            #cp_mediaserver_bins "vox" "mediaserver vox"

            # Server configuration does not need to be copied.
            #cp_files "$VMS_DIR/edge_firmware/rpi/maven/bpi/$BPI_MEDIASERVER_DIR" "etc" "$BPI_MEDIASERVER_DIR" "etc" "$VMS_DIR"

            exit 0
            ;;
        copy-c)
            find_VMS_DIR

            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"

            cp_lite_client_bins "mobile_client" "mobile_client exe"

            # Currently, "copy" verb copies only nx_vms build results.
            #cp_files "$VMS_DIR/$QT_PATH/lib" "*.so*" "$BPI_LIBS_DIR" "Qt libs" "$QT_PATH"
            #cp_lite_client_bins \
            #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,video,libexec,resources,translations}" \
            #    "{egldeviceintegrations,fonts,imageformats,platforms,qml,video,libexec,resources,translations}" \
            #    "mobile_client/bin Qt dirs"
            #cp_sysroot_libs "lib{opus,vpx,webp,webpdemux}.so*" "libs for web-engine"
            #cp_lite_client_bins "ff{mpeg,probe,server}" "ffmpeg executables"
            #cp_libs "ffmpeg" "lib/ffmpeg for proxydecoder"

            exit 0
            ;;
        copy-ut)
            find_vms_dir
            cp_libs "*.so*" "all libs except lib/ffmpeg for proxydecoder"
            cp_files "$VMS_DIR/build_environment/target-bpi/bin/debug" "*_ut" \
                "$BPI_MEDIASERVER_DIR/ut" "unit tests" "$VMS_DIR"
            exit $?
            ;;
        client)
            cp_lite_client_bins "mobile_client" "mobile_client exe"
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
            if [ "$2" = "" ]; then
                find_LIB_DIR
                LIB_NAME=$(basename "$LIB_DIR")
            else
                LIB_NAME="$2"
            fi
            cp_libs "lib$LIB_NAME.so*" "lib $LIB_NAME"
            exit $?
            ;;
        ini)
            bpi \
                touch /tmp/mobile_client.ini \&\& \
                touch /tmp/nx_media.ini \&\& \
                touch /tmp/ProxyVideoDecoder.ini \&\& \
                touch /tmp/proxydecoder.ini
            exit $?
            ;;
        #..........................................................................................
        ssh)
            shift
            bpi "$@"
            exit $?
            ;;
        run-c)
            shift
            bpi /opt/networkoptix/mediaserver/var/scripts/start_lite_client "$@"
            exit $?
            ;;
        kill-c)
            bpi killall mobile_client
            exit $?
            ;;
        start-s)
            shift
            bpi /etc/init.d/networkoptix-mediaserver start "$@"
            exit $?
            ;;
        stop-s)
            bpi /etc/init.d/networkoptix-mediaserver stop
            exit $?
            ;;
        start-c)
            shift
            bpi /etc/init.d/networkoptix-lite-client start "$@"
            exit $?
            ;;
        stop-c)
            bpi /etc/init.d/networkoptix-lite-client stop
            exit $?
            ;;
        start)
            shift
            bpi /etc/init.d/networkoptix-mediaserver start "$@"
            nx_echo
            bpi /etc/init.d/networkoptix-lite-client start "$@"
            exit $?
            ;;
        stop)
            bpi \
                /etc/init.d/networkoptix-lite-client stop \&\& \
                echo \&\& \
                /etc/init.d/networkoptix-mediaserver stop
            exit $?
            ;;
        run-ut)
            shift
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && fail "Test name not specified."
            local ARGS=("$@")
            
            echo "Running: $TEST_NAME ${ARGS[@]}"
            bpi "LD_LIBRARY_PATH=$BPI_MEDIASERVER_DIR/lib" \
                "$BPI_MEDIASERVER_DIR/ut/$TEST_NAME" "${ARGS[@]}"
            exit $?
            ;;
        #..........................................................................................
        vdp)
            shift
            bpi make -C "$BPI_PACKAGES_SRC_DIR/libvdpau-sunxi" "$@" \&\& echo "SUCCESS"
            exit $?
            ;;
        vdp-rdep)
            cd "$PACKAGES_DIR/libvdpau-sunxi-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/libvdpau-sunxi"/lib*so* lib/ || exit $?
            rdep -u
            exit $?
            ;;
        pd)
            shift
            bpi make -C "$BPI_PACKAGES_SRC_DIR/proxy-decoder" "$@" \&\& echo "SUCCESS"
            exit $?
            ;;
        pd-rdep)
            cd "$PACKAGES_DIR/proxy-decoder${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/proxy-decoder/libproxydecoder.so" lib/ || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/proxy-decoder/proxy_decoder.h" include/ || exit $?
            rdep -u
            exit $?
            ;;
        cedrus)
            shift
            if [ "$1" = "ump" ]; then
                shift
                bpi USE_UMP=1 make -C "$BPI_PACKAGES_SRC_DIR/libcedrus" "$@" \&\& echo "SUCCESS"
            else
                bpi make -C "$BPI_PACKAGES_SRC_DIR/libcedrus" "$@" \&\& echo "SUCCESS"
            fi
            exit $?
            ;;
        cedrus-rdep)
            cd "$PACKAGES_DIR/libcedrus-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_rsync "$PACKAGES_SRC_DIR/libcedrus"/lib*so* lib/ || exit $?
            rdep -u
            exit $?
            ;;
        ump)
            bpi \
                rm -r /tmp/libump \&\& \
                cp -r "$BPI_PACKAGES_SRC_DIR/libump" /tmp/ \&\& \
                cd /tmp/libump \&\& \
                dpkg-buildpackage -b \|\| \
                    echo "WARNING: Package build failed; manually installing .so and .h." \&\& \
                cp -r /tmp/libump/debian/tmp/usr /
            exit $?
            ;;
        ldp)
            shift
            bpi make -C "$BPI_PACKAGES_SRC_DIR/ldpreloadhook" "$@" \&\& echo "SUCCESS"
            exit $?
            ;;
        ldp-rdep)
            cd "$PACKAGES_DIR/ldpreloadhook-1.0${PACKAGE_SUFFIX}" || exit $?
            nx_sync "$PACKAGES_SRC_DIR/ldpreloadhook"/*.so* lib/ || exit
            rdep -u
            exit $?
            ;;
        #..........................................................................................
        rebuild)
            shift
            find_VMS_DIR
            cd "$VMS_DIR"
            mvn clean package -Dbox=bpi -Darch=arm -Dcloud.url="cloud-test.hdw.mx" "$@"
            exit $?
            ;;
        pack-short)
            shift
            pack_short "$1"
            exit $?
            ;;
        pack-full)
            shift
            pack_full "$1"
            exit $?
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
