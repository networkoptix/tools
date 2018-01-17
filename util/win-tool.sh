#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".win-toolrc"}"
: ${LINUX_TOOL="$(dirname "$0")/linux-tool.sh"}
: ${DEVELOP_DIR="$HOME/develop"}
: ${UBUNTU_DEVELOP_DIR="/S/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages"}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the target dir.
: ${BUILD_CONFIG=""} #< Path component after "bin/" and "lib/".
: ${MVN_BUILD_DIR="x64"} #< Name of the directories inside "nx_vms".
: ${NX_KIT_DIR="open/artifacts/nx_kit"} #< Path inside "nx_vms".
: ${TEMP_DIR="$(dirname $(mktemp `# dry run` -u))"}

#--------------------------------------------------------------------------------------------------

help_callback()
{
    cat \
<<EOF
Swiss Army Knife for Windows: execute various commands.
Use ~/$CONFIG to override workstation-dependent environment variables (see them in this script).
Usage: run via Cygwin from any dir inside the proper nx_vms dir:

 $(basename "$0") <options> <command>

$NX_HELP_TEXT_OPTIONS

Here <command> can be one of the following (if not, redirected to $(basename "$LINUX_TOOL")):

 apidoc [dev|prod] # Run apidoctool from devtools or from packages/any to generate api.xml.
 apidoc-rdep # Run tests and deploy apidoctool from devtools to packages/any.

 start-s [Release] [args] # Start mediaserver with [args].
 stop-s # Stop mediaserver.
 start-c [args] # Start desktop_client with [args].
 stop-c # Stop desktop_client.
 run-ut [Release] [all|test_name] [args] # Run all or the specified unit test via ctest.

 clean # Delete cmake build dir and all maven build dirs.
 mvn [args] # Call maven.
 gen [cmake-args] # Perform cmake generation.
 build [Release] [args] # Build via "cmake --build <dir> [--config Release] [args]".
 cmake [Release] [gen-args] # Perform cmake generation, then build via "cmake --build".
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

do_mvn() # "$@"
{
    mvn "$@" # No additional args needed like platform and box.
}

# Deduce CMake build dir out of VMS_DIR. Examples:
# nx -> nx-build
# /S/develop/nx -> nx-ubuntu-build
find_CMAKE_BUILD_DIR() # [-create]
{
    find_VMS_DIR

    case "$VMS_DIR" in
        "$UBUNTU_DEVELOP_DIR"/*)
            VMS_DIR_NAME=${VMS_DIR#$UBUNTU_DEVELOP_DIR/} #< Removing the prefix.
            CMAKE_BUILD_DIR="$DEVELOP_DIR/$VMS_DIR_NAME-ubuntu$BUILD_SUFFIX"
            ;;
        *)
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
            ;;
    esac


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

}

find_and_pushd_CMAKE_BUILD_DIR() # [-create]
{
    find_CMAKE_BUILD_DIR "$@"
    nx_pushd "$CMAKE_BUILD_DIR"
    nx_echo "+ cd \"$CMAKE_BUILD_DIR\"" #< Log "cd build-dir".
}

do_clean()
{
    find_CMAKE_BUILD_DIR

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

do_gen() # "$@"
{
    find_and_pushd_CMAKE_BUILD_DIR -create

    local -r CMAKE_CACHE="$CMAKE_BUILD_DIR/CMakeCache.txt"
    if [ -f "$CMAKE_CACHE" ]; then
        nx_verbose rm "$CMAKE_CACHE"
    fi

    nx_verbose cmake $(w "$VMS_DIR") -Ax64 -DrdepSync=OFF "$@"
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_build() # [Release] "$@"
{
    find_and_pushd_CMAKE_BUILD_DIR

    local CONFIGURATION_ARG=""
    [ "$1" == "Release" ] && { shift; CONFIGURATION_ARG="--config Release"; }

    time nx_verbose cmake --build $(w "$CMAKE_BUILD_DIR") $CONFIGURATION_ARG "$@"
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

    nx_verbose ctest $CONFIGURATION_ARG $TEST_ARG "$@"
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
        find_CMAKE_BUILD_DIR
        TARGET_DIR_DESCRIPTION="$CMAKE_BUILD_DIR (cmake)"
        API_XML="$CMAKE_BUILD_DIR/mediaserver_core/api.xml"
    fi

    local API_TEMPLATE_XML="$VMS_DIR/mediaserver_core/api/api_template.xml"

    [ ! -f "$API_TEMPLATE_XML" ] && nx_fail "Cannot open file $API_TEMPLATE_XML"

    local JAR_DEV="$DEVELOP_DIR/devtools/apidoctool/out/apidoctool.jar"
    local JAR_PROD="$PACKAGES_DIR/any/apidoctool/apidoctool.jar"
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
    local API_XML_W=$(w "$API_XML")
    if [ -z "$1" ]; then #< No other args - run apidoctool to generate documentation.
        nx_verbose java -jar "$JAR_W" -verbose code-to-xml -vms-path "$(w "$VMS_DIR")" \
            -template-xml "$(w "$API_TEMPLATE_XML")" -output-xml "$API_XML_W"
        RESULT=$?
    else #< Some args specified - run apidoctool with the specified args.
        nx_verbose java -jar "$JAR_W" "$@"
        RESULT=$?
    fi
    nx_echo
    nx_verbose cmake -E copy_if_different \
        "$API_XML_W" $(w "$CMAKE_BUILD_DIR/mediaserver_core/resources/static/") \
        || exit $?
    return $RESULT
}

do_apidoc_rdep() # "$@"
{
    local -r DEV_DIR="$DEVELOP_DIR/devtools/apidoctool"
    local -r JAR_DEV="$DEV_DIR/out/apidoctool.jar"
    local -r PACKAGE_DIR="$PACKAGES_DIR/any/apidoctool"
    local -r JAR_PROD="$PACKAGE_DIR/apidoctool.jar"
    local -r TEST_DIR="$DEV_DIR/test"

    nx_verbose java -jar "$(w "$JAR_DEV")" -verbose test -test-path "$(w "$TEST_DIR")" || exit $?

    nx_echo
    cp "$JAR_DEV" "$JAR_PROD" || exit $?

    nx_pushd "$PACKAGE_DIR"
    rdep -u || exit $?
    nx_echo
    nx_echo "SUCCESS: apidoctool tested and uploaded via rdep"
    nx_popd
}

build_and_test_nx_kit() # nx_kit_src_dir "$@"
{
    local SRC="$1"; shift
    nx_verbose cmake "$SRC" -G 'Unix Makefiles' -DCMAKE_C_COMPILER=gcc || return $?
    nx_verbose cmake --build . "$@" || return $?
    ./nx_kit_*
}

do_kit() # "$@"
{
    find_VMS_DIR

    # Recreate nx_kit build dir in $TEMP_DIR.
    local KIT_BUILD_DIR="$TEMP_DIR/nx_kit-build"
    rm -rf "$KIT_BUILD_DIR"
    mkdir -p "$KIT_BUILD_DIR" || exit $?
    nx_pushd "$KIT_BUILD_DIR"
    nx_echo "+ cd $KIT_BUILD_DIR"

    local KIT_SRC_DIR="$VMS_DIR/$NX_KIT_DIR"
    build_and_test_nx_kit "$KIT_SRC_DIR" || { local RESULT=$?; nx_popd; exit $?; }

    nx_popd
    rm -rf "$KIT_BUILD_DIR"

    nx_verbose rm -r "$PACKAGES_DIR/any/nx_kit/src"
    nx_verbose cp -r "$KIT_SRC_DIR/src" "$PACKAGES_DIR/any/nx_kit/" || exit $?
    nx_verbose cp -r "$KIT_SRC_DIR/nx_kit.cmake" "$PACKAGES_DIR/any/nx_kit/" || exit $?
    nx_echo
    nx_echo "SUCCESS: $NX_KIT_DIR/src and nx_kit.cmake copied to packages/any/"
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        #..........................................................................................
        apidoc)
            do_apidoc "$@"
            ;;
        apidoc-rdep)
            do_apidoc_rdep "$@"
            ;;
        #..........................................................................................
        start-s)
            find_and_pushd_CMAKE_BUILD_DIR
            local CONFIGURATION="Debug"
            [ "$1" == "Release" ] && { shift; CONFIGURATION="Release"; }
            PATH="$PATH:$PACKAGES_DIR/windows-x64/qt-5.6.1-1/bin"
            nx_verbose "$CONFIGURATION"/bin/mediaserver -e
            nx_popd
            ;;
        stop-s)
            # TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        start-c)
            # TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            #local CONFIGURATION="Debug"
            #[ "$1" == "Release" ] && { shift; CONFIGURATION="Release"; }
            #find_and_pushd_CMAKE_BUILD_DIR
            #PATH="$PATH:$PACKAGES_DIR/windows-x64/qt-5.6.1-1/bin"
            #nx_verbose "$CONFIGURATION"/bin/desktop_client
            ;;
        stop-c)
            # TODO: Decide on better impl.
            nx_fail "Command not implemented yet."
            ;;
        run-ut)
            do_run_ut "$@"
            ;;
        #..........................................................................................
        clean)
            do_clean "$@"
            ;;
        mvn)
            do_mvn "$@"
            ;;
        gen)
            do_gen "$@"
            ;;
        build)
            do_build "$@"
            ;;
        cmake)
            local CONFIGURATION_ARG=""
            [ "$1" == "Release" ] && { shift; CONFIGURATION_ARG="Release"; }
            do_gen "$@" || exit $?
            do_build $CONFIGURATION_ARG
            ;;
        #..........................................................................................
        *)
            "$LINUX_TOOL" "$COMMAND" "$@"
            ;;
    esac
}

nx_run "$@"
