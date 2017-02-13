#!/bin/bash
source "$(dirname $0)/utils.sh"

#--------------------------------------------------------------------------------------------------
# Configuration

DEVELOP_DIR="$HOME/develop"

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for Android Mobile Client: execute various commands.
Usage: run from any dir inside nx_vms:
$(basename $0) [--verbose] <command>
Here <command> can be one of the following:

device - Check Android device is connected and mount it to '/android'.

deploy - Rebuild apk, reinstall apk, launch the app.
run - Lanuch the app.
stop - Force-stop the app.
log - Show Mobile Client log via filtering 'adb logcat'.
uninstall - Uninstall apk from Android device.
install - Install apk to Android device.

java - After changing .java: copy sources so that 'deploy' will rebuild classes.
rebuild ... - Perform 'mvn clean package' with the required parameters.
unpack <path/to/new/dir> - Unpack existing .apk, including dex2jar.
EOF
}

#--------------------------------------------------------------------------------------------------

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR $(basename "$DEVELOP_DIR") \
        "Run this script from any dir inside your nx_vms repo dir."
}

#--------------------------------------------------------------------------------------------------

mount_adb()
{
    ADB_DEVICES="$(adb devices)"
    if [ -z  "$(echo "$ADB_DEVICES" |grep -w "device")" ]; then
        fail "Unable to access Android device via adb."
    fi
    nx_echo "$ADB_DEVICES"
}

do_run()
{
    adb shell am start -n com.networkoptix.nxwitness/.QnActivity
}

do_stop()
{
    adb shell am force-stop com.networkoptix.nxwitness
}

do_uninstall()
{
    adb uninstall com.networkoptix.nxwitness || exit $?
}

do_install()
{
    find_VMS_DIR

    # Name of apk depends on the repo branch.
    adb install -r "$VMS_DIR/client/mobile_client/arm"/*client*.apk || exit $?
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        #..........................................................................................
        device)
            mount_adb || exit $?
            nx_echo "SUCCESS: Android device is accessible."
            exit 0
            ;;
        #..........................................................................................
        deploy)
            find_VMS_DIR
            mount_adb || exit $?

            rm -rf "$VMS_DIR/build_environment/target/lib/debug/libmobile_client.so"
            rm -rf "$VMS_DIR/client/mobile_client/arm/apk/bin"/*.apk
            rm -rf "$VMS_DIR/client/mobile_client/arm"/*.apk

            pushd "$VMS_DIR/client/mobile_client/arm" >/dev/null
            ./deploy-android.sh
            ERR=$?
            popd >/dev/null
            [ "$ERR" -gt 0 ] && exit $ERR

            do_uninstall || exit $?
            do_install || exit $?

            nx_echo

            do_run || exit $?

            nx_echo "SUCCESS deploying"
            exit 0
            ;;
        run)
            do_run
            exit $?
            ;;
        stop)
            do_stop
            exit $?
            ;;
        #..........................................................................................
        log)
            adb logcat |grep --line-buffered "Mobile Client" \
                |sed -u 's/.*Mobile Client: //' |sed -u 's/.*QnLogLevel)): //'
            exit $?
            ;;
        uninstall)
            mount_adb || exit $?
            do_uninstall
            exit $?
            ;;
        install)
            mount_adb || exit $?
            do_install
            exit $?
            ;;
        #..........................................................................................
        java)
            find_VMS_DIR
            MOBILE_CLIENT="$VMS_DIR/client/mobile_client"
            rm -rf "$MOBILE_CLIENT/arm/android/src" || exit $?
            cp -r "$MOBILE_CLIENT/maven/bin-resources/android/src" "$MOBILE_CLIENT/arm/android/" \
                || exit $?
            nx_echo "SUCCESS preparing .java for 'deploy'"
            exit 0
            ;;
        rebuild)
            find_VMS_DIR
            cd "$VMS_DIR"
            mvn clean package \
                -Dbox=android -Darch=arm -Dnewmobile=true -Dcloud.url="cloud-test.hdw.mx" "$@"
            exit $?
            ;;
        unpack)
            UNPACK_DIR="$1"
            [ -z "$UNPACK_DIR" ] && nx_fail "Target dir not specified."

            find_VMS_DIR

            mkdir -p "$UNPACK_DIR"
            cp "$VMS_DIR/client/mobile_client/arm"/*client.apk "$UNPACK_DIR/apk.zip" || exit $?
            unzip "$UNPACK_DIR/apk.zip" -d "$UNPACK_DIR/" || exit $?
            rm "$UNPACK_DIR/apk.zip" || exit $?
            mkdir -p "$UNPACK_DIR/classes" || exit $?
            d2j-dex2jar.sh "$UNPACK_DIR/classes.dex" -o "$UNPACK_DIR/classes/classes.zip" || exit $?
            unzip "$UNPACK_DIR/classes/classes.zip" -d "$UNPACK_DIR/classes/" || exit $?
            rm "$UNPACK_DIR/classes/classes.zip" || exit $?

            nx_echo
            nx_echo "Unpacked;  dex2jarred to $UNPACK_DIR/classes"
            exit 0
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
