#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".tx1-toolrc"}"
: ${DEVELOP_DIR="$HOME/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages/linux-x64"}
: ${PACKAGES_ANY_DIR="$DEVELOP_DIR/buildenv/packages/any"}
: ${QT_DIR="$PACKAGES_DIR/qt-5.6.2"}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the cmake build dir.
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

apidoc target [dev|prod] # Run apidoctool from devtools or from packages/any to generate api.xml.
kit [cmake-build-args] # Build artifacts/nx_kit, run tests and deploy its src to the rdep artifact.

start-s [args] # Start mediaserver with [args].
stop-s # Stop mediaserver.
start-c [args] # Start desktop_client with [args].
stop-c # Stop desktop_client.
run-ut target [Release] [all|test_name] [args] # Run all or the specified unit test via ctest.

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
    local TARGET="$1"
    case "$VMS_DIR" in *-"$TARGET")
        CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
        return
    esac
    CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX-$TARGET"
}

get_TARGET() # "$1" && shift
{
    local TARGET="$1"
    [ -z "$TARGET" ] && nx_fail "Target should be specified as the first arg."
}

clean() # target
{
    find_VMS_DIR
    get_TARGET "$1" && shift
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
    find_VMS_DIR
    get_TARGET "$1" && shift
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
    find_VMS_DIR
    get_TARGET "$1" && shift
    get_CMAKE_BUILD_DIR "$TARGET"
    [ ! -d "$CMAKE_BUILD_DIR" ] && nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake first."

    nx_logged cmake --build "$CMAKE_BUILD_DIR" "$@"
}

do_run_ut() # target [all|TestName] "$@"
{
    get_TARGET "$1" && shift
    find_and_pushd_CMAKE_BUILD_DIR

    local TEST_NAME="$1" && shift

    local TEST_ARG
    case "$TEST_NAME" in
        all) TEST_ARG="";;
        "") nx_fail "Expected either 'all' or a test name as the first arg.";;
        *) TEST_ARG="-R $TEST_NAME";;
    esac

    nx_logged ctest $TEST_ARG "$@"
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_apidoc() # target [dev|prod] "$@"
{
    find_VMS_DIR
    get_TARGET "$1" && shift

    local TOOL="$1" && shift

    local TARGET_DIR_DESCRIPTION="$VMS_DIR (maven)"
    local API_XML="$VMS_DIR/mediaserver_core/$MVN_BUILD_DIR/resources/static/api.xml"
    if [ ! -f "$API_XML" ]; then #< Assume cmake instead of maven.
        get_CMAKE_BUILD_DIR "$TARGET"
        TARGET_DIR_DESCRIPTION="$CMAKE_BUILD_DIR (cmake)"
        API_XML="$CMAKE_BUILD_DIR/mediaserver_core/api.xml"
    fi

    local API_TEMPLATE_XML="$VMS_DIR/mediaserver_core/api/api_template.xml"

    [ ! -f "$API_TEMPLATE_XML" ] && nx_fail "Cannot open file $API_TEMPLATE_XML"

    local JAR_DEV="$VMS_DIR/../devtools/apidoctool/out/apidoctool.jar"
    local JAR_PROD="$VMS_DIR/../buildenv/packages/any/apidoctool/apidoctool.jar"
    if [[ $TOOL = "dev" || ($TOOL = "" && -f "$JAR_DEV") ]]; then
        local JAR="$JAR_DEV"
        nx_echo "Executing apidoctool from devtools/ in $TARGET_DIR_DESCRIPTION"
    elif [[ $TOOL = "prod" || $TOOL = "" ]]; then
        local JAR="$JAR_PROD"
        nx_echo "Executing apidoctool from packages/any/ in $TARGET_DIR_DESCRIPTION"
    else
        nx_fail "Invalid apidoctool location \"$TOOL\": expected \"dev\" or \"prod\"."
    fi

    if [ -z "$1" ]; then #< No other args - run apidoctool to generate documentation.
        nx_logged java -jar "$JAR" -verbose code-to-xml -vms-path "$VMS_DIR" \
            -template-xml "$API_TEMPLATE_XML" -output-xml "$API_XML"
    else #< Some args specified - run apidoctool with the specified args.
        nx_logged java -jar "$JAR" "$@"
    fi
}

do_kit() # "$@"
{
    find_VMS_DIR

    # Recreate nx_kit build dir in /tmp.
    local KIT_BUILD_DIR="/tmp/nx_kit-build"
    rm -rf "$KIT_BUILD_DIR"
    mkdir -p "$KIT_BUILD_DIR" || exit $?
    nx_logged cd "$KIT_BUILD_DIR"

    local KIT_SRC_DIR="$VMS_DIR/artifacts/nx_kit"

    nx_logged cmake "$KIT_SRC_DIR" -GNinja || exit $?
    nx_logged cmake --build . "$@" || exit $?
    ./nx_kit_test || exit $?
    cp -r "$KIT_SRC_DIR/src" "$PACKAGES_ANY_DIR/nx_kit/" || exit $?
    nx_echo
    nx_echo "SUCCESS: artifacts/nx_kit/src copied to packages/any/"

    rm -rf "$KIT_BUILD_DIR"
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
        apidoc)
            do_apidoc "$@"
            ;;
        kit)
            do_kit "$@"
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
            do_run_ut "$@"
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
