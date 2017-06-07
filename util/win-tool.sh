#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".win-toolrc"}"
: ${DEVELOP_DIR="$HOME/develop"}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the target dir.
: ${BUILD_CONFIG=""} #< Path component after "bin/" and "lib/".
: ${PACKAGE_SUFFIX=""}
: ${MVN_BUILD_DIR="x64"} #< Name of the directories inside "nx_vms".

#--------------------------------------------------------------------------------------------------

help()
{
    cat <<EOF
Swiss Army Knife for Windows: execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run via Cygwin from any dir inside the proper nx_vms dir:

$(basename "$0") [--verbose] <command>

Here <command> can be one of the following:

ini # Create empty .ini files (to be filled with defauls) in $TEMP - should point to %TEMP%.

apidoc [dev|prod] # Run apidoctool from devtools or from packages/any to generate api.xml.
kit [cmake-build-args] # Build artifacts/nx_kit, run tests and deploy its src to the rdep artifact.

start-s [args] # Start mediaserver with [args].
stop-s # Stop mediaserver.
start-c [args] # Start desktop_client with [args].
stop-c # Stop desktop_client.
run-ut [Release] [all|test_name] [args] # Run all or the specified unit test via ctest.

clean # Delete cmake build dir and all maven build dirs.
mvn [args] # Call maven.
cmake [cmake-args] # Call cmake in cmake build dir.
build [Release] [args] # Build via "cmake --build <dir> [--config Release] [args]".
EOF
}

#--------------------------------------------------------------------------------------------------

# Convert cygwin path to windows path for external tools.
w() # "$@"
{
    cygpath -w "$@"
}

# If not done yet, scan from current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
find_VMS_DIR()
{
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" \
        "Run this script from any dir inside your nx_vms repo dir."
}

do_clean()
{
    find_VMS_DIR
    local CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"

    if [ -d "$CMAKE_BUILD_DIR" ]; then
        nx_echo "Deleting cmake build dir: $CMAKE_BUILD_DIR"
        rm -r "$CMAKE_BUILD_DIR"
    fi

    local MVN_TARGET_DIR="target"

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

do_mvn() # "$@"
{
    mvn "$@" # No additional args needed like platform and box.
}

find_and_pushd_CMAKE_BUILD_DIR() # [-create]
{
    find_VMS_DIR
    CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"

    case "$1" in
        -create)
            if [ -d "$CMAKE_BUILD_DIR" ]; then
                nx_echo "WARNING: Dir $CMAKE_BUILD_DIR already exists."
            else
                mkdir -p "$CMAKE_BUILD_DIR"
            fi
            ;;
        "")
            if [ ! -d "$CMAKE_BUILD_DIR" ]; then
                nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake first."
            fi
            ;;
        *)
            nx_fail "INTERNAL ERROR: find_CMAKE_BUILD_DIR: Expected no args or '-create'."
            ;;
    esac

    nx_pushd "$CMAKE_BUILD_DIR"
    nx_echo "+ cd \"$CMAKE_BUILD_DIR\"" #< Log "cd build-dir".
}

do_cmake() # "$@"
{
    find_and_pushd_CMAKE_BUILD_DIR -create

    nx_logged cmake "$@" -Ax64 $(w "$VMS_DIR")
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_build() # [Release] "$@"
{
    find_and_pushd_CMAKE_BUILD_DIR

    local CONFIGURATION_ARG=""
    [ "$1" == "Release" ] && { shift; CONFIGURATION_ARG="--config Release"; }

    nx_logged cmake --build $(w "$CMAKE_BUILD_DIR") $CONFIGURATION_ARG "$@"
}

do_run_ut() # [Release] [all|TestName] "$@"
{
    find_and_pushd_CMAKE_BUILD_DIR

    local TEST_NAME="$1" && shift
    local TEST_ARG
    case "$TEST_NAME" in
        all) TEST_ARG="";;
        "") nx_fail "Expected either 'all' or a test name as the first arg.";;
        *) TEST_ARG="-R $TEST_NAME";;
    esac

    local CONFIGURATION_ARG="-C Debug"
    [ "$1" == "Release" ] && { shift; CONFIGURATION_ARG="-C Release"; }

    nx_logged ctest $CONFIGURATION_ARG $TEST_ARG "$@"
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_apidoc() # [dev|prod] "$@"
{
    find_VMS_DIR
    local TOOL="$1" && shift

    local TARGET_DIR_DESCRIPTION="$VMS_DIR (maven)"
    local API_XML="$VMS_DIR/mediaserver_core/$MVN_BUILD_DIR/resources/static/api.xml"
    if [ ! -f "$API_XML" ]; then #< Assume cmake instead of maven.
        find_and_pushd_CMAKE_BUILD_DIR
        nx_popd
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

    local JAR_W=$(w "$JAR")
    if [ -z "$1" ]; then #< No other args - run apidoctool to generate documentation.
        nx_logged java -jar "$JAR_W" -verbose code-to-xml -vms-path $(w "$VMS_DIR") \
            -template-xml $(w "$API_TEMPLATE_XML") -output-xml $(w "$API_XML")
    else #< Some args specified - run apidoctool with the specified args.
        nx_logged java -jar "$JAR_W" "$@"
    fi
}

do_kit() # "$@"
{
    find_VMS_DIR

    find_and_pushd_CMAKE_BUILD_DIR -create

    # Recreate nx_kit build dir inside cmake build dir.
    local KIT_BUILD_DIR="$CMAKE_BUILD_DIR/artifacts/nx_kit"
    rm -rf "$KIT_BUILD_DIR"
    mkdir -p "$KIT_BUILD_DIR" || exit $?
    nx_logged cd "$KIT_BUILD_DIR"

    local KIT_SRC_DIR="$VMS_DIR/artifacts/nx_kit"

    local KIT_SRC_DIR_W=$(w "$KIT_SRC_DIR")
    nx_logged cmake "$KIT_SRC_DIR_W" -G 'Unix Makefiles' -DCMAKE_C_COMPILER=gcc.exe || exit $?
    nx_logged cmake --build . "$@" || exit $?
    ./nx_kit_test || exit $?
    cp -r "$KIT_SRC_DIR/src" "$PACKAGES_ANY_DIR/nx_kit/" || exit $?
    nx_echo
    nx_echo "SUCCESS: artifacts/nx_kit/src copied to packages/any/"

    nx_popd
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        ini)
            touch $TEMP/nx_media.ini
            touch $TEMP/analytics.ini
            touch $TEMP/mobile_client.ini
            touch $TEMP/nx_media.ini
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
            // TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        start-c)
            // TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        stop-c)
            // TODO: Decide on better impl.
            nx_fail "Command not implemented yet."
            ;;
        run-ut)
            do_run_ut "$@"
            ;;
        #..........................................................................................
        clean)
            do_clean
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
