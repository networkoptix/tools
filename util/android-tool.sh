#!/bin/bash

GVFS_PATH="/run/user/1000/gvfs/mtp:host=*"

#--------------------------------------------------------------------------------------------------

show_help_and_exit()
{
    echo "Swiss Army Knife for Android Mobile Client: execute various commands."
    echo "Usage: run from any dir inside nx_vms:"
    echo $0 "<command>"
    echo "Here <command> can be one of the following:"
    echo
    echo "device - Check Android device is connected and mount it to '/android'."
    echo
    echo "deploy - Rebuild apk, reinstall apk, launch the app."
    echo "run - Lanuch the app."
    echo "stop - Force-stop the app."
    echo "log - Show Mobile Client log via filtering 'adb logcat'."
    echo "uninstall - Uninstall apk from Android device."
    echo "install - Install apk to Android device."
    echo
    echo "java - After changing .java: copy sources so that 'deploy' will rebuild classes."
    echo "rebuild ... - Perform 'mvn clean package' with the required parameters."
    echo "unpack <path/to/new/dir> - Unpack existing .apk, including dex2jar."
    exit 0
}

#--------------------------------------------------------------------------------------------------

# Check that the specified file exists. Needed to support globs in the filename.
exists_glob()
{
    [ -e "$1" ]
}

writeln()
{
    echo "$1" |sed -e "s#$HOME/#~/#g"
}

fail()
{
    writeln "ERROR: $@" >&2
    exit 1
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
        fail "Run this script from any dir inside nx_vms."
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
        fail "Either specify lib name or cd to common_libs/<lib_name>."
    fi
}

#--------------------------------------------------------------------------------------------------

mount_adb()
{
    ADB_DEVICES="$(adb devices)"
    if [ -z  "$(echo "$ADB_DEVICES" |grep -w "device")" ]; then
        fail "Unable to access Android device via adb."
    fi
    echo "$ADB_DEVICES"

# TODO: GVFS works unstably, and does not provide write access, thus, disabled.
#    sudo rm -rf /android
#    if ! exists_glob $GVFS_PATH; then
#        fail "Android device is not gvfs-mounted at $GVFS_PATH"
#    fi
#    sudo ln -s "$GVFS_PATH/Phone" /android
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
    find_vms_dir

    # Name of apk depends on the repo branch.
    adb install -r "$VMS_DIR/client/mobile_client/arm"/*client*.apk || exit $?
}

#--------------------------------------------------------------------------------------------------

main()
{
    if [ "$#" = "0" -o "$1" = "-h" -o "$1" = "--help" ]; then
        show_help_and_exit
    fi

    if [ "$#" -ge "1" ]; then
        case "$1" in
            #..........................................................................................
            "device")
                mount_adb || exit $?
                writeln "SUCCESS: Android device is accessible."
                exit 0
                ;;
            #..........................................................................................
            "deploy")
                find_vms_dir
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

                writeln

                do_run || exit $?

                writeln "SUCCESS deploying"
                exit 0
                ;;
            "run")
                do_run
                exit $?
                ;;
            "stop")
                do_stop
                exit $?
                ;;
            #..........................................................................................
            "log")
                adb logcat |grep --line-buffered "Mobile Client" \
                    |sed -u 's/.*Mobile Client: //' |sed -u 's/.*QnLogLevel)): //'
                exit $?
                ;;
            "uninstall")
                mount_adb || exit $?
                do_uninstall
                exit $?
                ;;
            "install")
                mount_adb || exit $?
                do_install
                exit $?
                ;;
            #..........................................................................................
            "java")
                find_vms_dir
                MOBILE_CLIENT="$VMS_DIR/client/mobile_client"
                rm -rf "$MOBILE_CLIENT/arm/android/src" || exit $?
                cp -r "$MOBILE_CLIENT/maven/bin-resources/android/src" "$MOBILE_CLIENT/arm/android/" \
                    || exit $?
                writeln "SUCCESS preparing .java for 'deploy'"
                exit 0
                ;;
            "rebuild")
                shift
                find_vms_dir
                cd "$VMS_DIR"
                mvn clean package \
                    -Dbox=android -Darch=arm -Dnewmobile=true -Dcloud.url="cloud-test.hdw.mx" "$@"
                exit $?
                ;;
            "unpack")
                shift
                UNPACK_DIR="$1"
                [ -z "$UNPACK_DIR" ] && fail "Target dir not specified."

                find_vms_dir

                mkdir -p "$UNPACK_DIR"
                cp "$VMS_DIR/client/mobile_client/arm"/*client.apk "$UNPACK_DIR/apk.zip" || exit $?
                unzip "$UNPACK_DIR/apk.zip" -d "$UNPACK_DIR/" || exit $?
                rm "$UNPACK_DIR/apk.zip" || exit $?
                mkdir -p "$UNPACK_DIR/classes" || exit $?
                d2j-dex2jar.sh "$UNPACK_DIR/classes.dex" -o "$UNPACK_DIR/classes/classes.zip" || exit $?
                unzip "$UNPACK_DIR/classes/classes.zip" -d "$UNPACK_DIR/classes/" || exit $?
                rm "$UNPACK_DIR/classes/classes.zip" || exit $?

                echo
                echo "Unpacked;  dex2jarred to $UNPACK_DIR/classes"
                exit 0
                ;;
            #..........................................................................................
            *)
                fail "Unknown argument: $1"
                ;;
        esac
    else
        fail "Invalid arguments. Run with -h for help."
    fi
}

main "$@"
