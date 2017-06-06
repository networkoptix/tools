#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".tx1-toolrc"}"
: ${DEVELOP_DIR="$HOME/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/linux-x64"}
: ${PACKAGES_ANY_DIR="$DEVELOP_DIR/buildenv/packages/any"}
: ${QT_DIR="$PACKAGES_DIR/qt-5.6.2"}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the target dir.
: ${BUILD_CONFIG=""} #< Path component after "bin/" and "lib/".
: ${PACKAGE_SUFFIX=""}
: ${CMAKE_GEN="Ninja"} #< Used for cmake generator and (lower-case) for "m" command.

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for Linux: execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

$(basename "$0") [--verbose] <command>

Here <command> can be one of the following:

ini # Create empty .ini files in /tmp (to be filled with defauls).

start-s [args] # Start mediaserver with [args].
stop-s # Stop mediaserver.
start-c [args] # Start desktop_client with [args].
stop-c # Stop desktop_client.
run-ut test_name [args] # Run the unit test with strict expectations.

clean # Delete cmake build dir and all maven build dirs.
mvn [args] # Call maven.
cmake target [cmake-args] # Call cmake in cmake build dir. For linux, use target "linux".
build target # Build via "cmake --build".
EOF
}

#--------------------------------------------------------------------------------------------------

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" \
        "Run this script from any dir inside your nx_vms repo dir."
}

do_mvn() # "$@"
{
    mvn "$@" # No additional args needed like platform and box.
}

# E.g. nx_vms -> nx_vms-build-isd; nx_vms-bpi -> nx_vms-bpi-build.
# [in] VMS_DIR
get_CMAKE_BUILD_DIR() # target
{
    local TARGET="$1"; shift
    case "$VMS_DIR" in *-"$TARGET")
        CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
        return
    esac
    CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX-$TARGET"
}

clean() # target
{
    local TARGET="$1"; shift
    [ -z "$TARGET" ] && nx_fail "Target should be specified as the first arg."
    find_VMS_DIR
    get_CMAKE_BUILD_DIR "$TARGET"

    if [ -d "$CMAKE_BUILD_DIR" ]; then
        nx_echo "Deleting cmake build dir: $CMAKE_BUILD_DIR"
        rm -r "$CMAKE_BUILD_DIR"
    fi

    case "$TARGET" in
        linux) MVN_TARGET_DIR="target"; MVN_BUILD_DIR="x64";;
        tx1) MVN_TARGET_DIR=""; MVN_BUILD_DIR="";; #< Maven not supported for tx1.
        bpi|edge1|rpi|bananapi) MVN_TARGET_DIR="target-$TARGET"; MVN_BUILD_DIR="arm-$TARGET";;
        android) MVN_TARGET_DIR="target"; MVN_BUILD_DIR="arm";;
        ios) MVN_TARGET_DIR=""; MVN_BUILD_DIR="";; #< TODO
        *) nx_fail "Unsupported target [$TARGET].";;
    esac

    nx_pushd "$VMS_DIR"

    if [ -d "$MVN_TARGET_DIR" ]; then
        nx_echo "Deleting maven target dir: $MVN_TARGET_DIR"
        rm -r "$MVN_TARGET_DIR"
    fi

    local MVN_B_E_TARGET_DIR="build_environment/$MVN_TARGET_DIR"
    if [ -d "$MVN_B_E_TARGET_DIR" ]; then
        nx_echo "Deleting maven target dir: $MVN_B_E_TARGET_DIR"
        rm -r "$MVN_B_E_TARGET_DIR"
    fi

    local BUILD_DIRS=()
    nx_find_files BUILD_DIRS -type d -name "$MVN_BUILD_DIR" \
        ! -path "./.hg/*" ! -path "./artifacts/*"
    local DIR
    for DIR in "${BUILD_DIRS[@]}"; do
        nx_echo "Deleting maven build dir: $DIR"
        rm -r "$DIR"
    done

    nx_popd
}

do_cmake() # target "$@"
{
    local TARGET="$1"; shift
    [ -z "$TARGET" ] && nx_fail "Target should be specified as the first arg."
    find_VMS_DIR
    get_CMAKE_BUILD_DIR "$TARGET"
    [ -d "$CMAKE_BUILD_DIR" ] && nx_echo "WARNING: Dir $CMAKE_BUILD_DIR already exists."
    mkdir -p "$CMAKE_BUILD_DIR"

    nx_pushd "$CMAKE_BUILD_DIR"
    local TARGET_OPTION=""
    [ "$TARGET" != "linux" ] && TARGET_OPTION="-DtargetDevice=$TARGET"
    local GENERATOR_OPTION=""
    [ ! -z "$CMAKE_GEN" ] && GENERATOR_OPTION="-G$CMAKE_GEN"

    nx_logged cmake "$@" "$GENERATOR_OPTION" "$TARGET_OPTION" "$VMS_DIR"
    local RESULT=$?

    nx_popd
    return "$RESULT"
}

do_build() # target
{
    local TARGET="$1"; shift
    [ -z "$TARGET" ] && nx_fail "Target should be specified as the first arg."
    find_VMS_DIR
    get_CMAKE_BUILD_DIR "$TARGET"
    [ ! -d "$CMAKE_BUILD_DIR" ] && nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake first."

    nx_logged cmake --build "$CMAKE_BUILD_DIR" "$@"
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        ini)
            touch /tmp/nx_media.ini
            touch /tmp/analytics.ini
            touch /tmp/mobile_client.ini
            touch /tmp/nx_media.ini
            ;;
        #..........................................................................................
        start-s)
            // TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        stop-s)
            // TODO: Decide on better impl.
            sudo killall -9 mediaserver
            ;;
        start-c)
            // TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        stop-c)
            // TODO: Decide on better impl.
            sudo killall -9 desktop_client
            ;;
        run-ut)
            find_VMS_DIR
            local TEST_NAME="$1"
            shift
            [ -z "$TEST_NAME" ] && nx_fail "Test name not specified."

            // TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            #local TEST_PATH="$VMS_DIR$BUILD_SUFFIX/ut/$TEST_NAME"
            #echo "Running: $TEST_PATH $@"
            #LD_LIBRARY_PATH="$LIBS_DIR" "$TEST_PATH" "$@"
            ;;
        #..........................................................................................
        clean)
            clean "$@"
            ;;
        mvn)
            do_mvn "$@"
            ;;
        cmake)
            do_cmake "$@"
            ;;
        build)
            do_build "$@"
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
