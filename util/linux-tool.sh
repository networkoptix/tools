#!/bin/bash
source "$(dirname $0)/utils.sh"

nx_load_config "${CONFIG=".tx1-toolrc"}"
: ${DEVELOP_DIR="$HOME/develop"}
: ${WIN_DEVELOP_DIR="/C/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages"}
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the cmake build dir.
: ${BUILD_CONFIG=""} #< Path component after "bin/" and "lib/".
: ${CMAKE_GEN="Ninja"} #< Used for cmake generator and (lower-case) for "m" command.
: ${NX_KIT_DIR="open/artifacts/nx_kit"} #< Path inside "nx_vms".
: ${LA_HDW_MX_USER="$USER"} #< Username at la.hdw.mx.

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
kit [cmake-build-args] # $NX_KIT_DIR: build, test, copy src to artifact.
kit-rdep # Deploy $PACKAGES_DIR/any/nx_kit via "rdep -u".

start-s [args] # Start mediaserver with [args].
stop-s # Stop mediaserver.
start-c [args] # Start desktop_client with [args].
stop-c # Stop desktop_client.
run-ut target [all|test_name] [args] # Run all or the specified unit test via ctest.

clean # Delete cmake build dir and all maven build dirs.
mvn [args] # Call maven.
gen target [Release] [cmake-args] # Perform cmake generation. For linux-x64, use target "linux".
build target # Build via "cmake --build <dir>".
cmake target [Release] [gen-args] # Perform cmake generation, then build via "cmake --build".
test-installer target original/archives/dir # Build installer and test to equal the original.
print-dirs target # Print VMS_DIR and CMAKE_BUILD_DIR for the specified target, on separate lines.
tunnel ip1 [ip2]... # Create ssh tunnel to Burbank for the specified Burbank IP addresses.
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

# Deduce CMake build dir out of VMS_DIR and targetDevice (box). Examples:
# nx -> nx-build-isd
# nx-bpi -> nx-bpi-build.
# /C/develop/nx -> nx-win-build-linux
# [in] VMS_DIR
get_CMAKE_BUILD_DIR() # target
{
    local TARGET="$1"
    case "$VMS_DIR" in
        *-"$TARGET")
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
            ;;
        "$WIN_DEVELOP_DIR"/*)
            VMS_DIR_NAME=${VMS_DIR#$WIN_DEVELOP_DIR/} #< Removing the prefix.
            CMAKE_BUILD_DIR="$DEVELOP_DIR/$VMS_DIR_NAME-win$BUILD_SUFFIX-$TARGET"
            ;;
        *)
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX-$TARGET"
            ;;
    esac
}

# [out] TARGET
# [out] MVN_TARGET_DIR
# [out] MVN_BUILD_DIR
get_TARGET() # "$1" && shift
{
    TARGET="$1"
    [ -z "$TARGET" ] && nx_fail "Target should be specified as the first arg."

    case "$TARGET" in
        linux) MVN_TARGET_DIR="target"; MVN_BUILD_DIR="x64"; BOX=""; ARCH="x64";;
        tx1) MVN_TARGET_DIR=""; MVN_BUILD_DIR=""; BOX=""; ARCH="";; #< tx1 is cmake-only
        bpi) MVN_TARGET_DIR="target-bpi"; MVN_BUILD_DIR="arm-bpi"; BOX="bpi"; ARCH="arm";;
        edge1) MVN_TARGET_DIR="target-edge1"; MVN_BUILD_DIR="arm-edge1"; BOX="edge1"; ARCH="arm";;
        rpi) MVN_TARGET_DIR="target-rpi"; MVN_BUILD_DIR="arm-rpi"; BOX="rpi"; ARCH="arm";;
        bananapi) MVN_TARGET_DIR="target-bananapi"; MVN_BUILD_DIR="arm-bananapi"; BOX="bananapi"; ARCH="arm";;
        android) MVN_TARGET_DIR="target"; MVN_BUILD_DIR="arm"; BOX="android"; ARCH="arm";;
        ios) MVN_TARGET_DIR=""; MVN_BUILD_DIR=""; BOX=""; ARCH="";; #< TODO: Support ios.
        *) nx_fail "Unsupported target [$TARGET].";;
    esac
}

do_clean() # target
{
    find_VMS_DIR
    get_TARGET "$1" && shift
    get_CMAKE_BUILD_DIR "$TARGET"

    if [ -d "$CMAKE_BUILD_DIR" ]; then
        nx_echo "Deleting cmake build dir: $CMAKE_BUILD_DIR"
        rm -r "$CMAKE_BUILD_DIR"
    fi

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

do_gen() # target [Release] "$@"
{
    find_VMS_DIR

    get_TARGET "$1" && shift

    local CONFIGURATION_ARG=""
    [ "$1" = "Release" ] && { shift; CONFIGURATION_ARG="-DCMAKE_BUILD_TYPE=Release"; }

    get_CMAKE_BUILD_DIR "$TARGET"
    [ -d "$CMAKE_BUILD_DIR" ] && nx_echo "WARNING: Dir $CMAKE_BUILD_DIR already exists."
    mkdir -p "$CMAKE_BUILD_DIR"

    nx_pushd "$CMAKE_BUILD_DIR"
    nx_echo "+ cd \"$CMAKE_BUILD_DIR\"" #< Log "cd build-dir".
    local TARGET_ARG=""
    [ "$TARGET" != "linux" ] && TARGET_ARG="-DtargetDevice=$TARGET"

    # TODO: Remove when the branch "analytics" is merged into default.
    if [ "$TARGET" = "tx1" ]; then
        TARGET_ARG="-DCMAKE_TOOLCHAIN_FILE=$VMS_DIR/cmake/toolchain/tx1.cmake"
    fi

    local GENERATOR_ARG=""
    [ ! -z "$CMAKE_GEN" ] && GENERATOR_ARG="-G$CMAKE_GEN"

    nx_verbose cmake "$VMS_DIR" "$@" $GENERATOR_ARG $TARGET_ARG $CONFIGURATION_ARG
    local RESULT=$?

    nx_popd
    return "$RESULT"
}

do_build() # target
{
    find_VMS_DIR
    get_TARGET "$1" && shift
    get_CMAKE_BUILD_DIR "$TARGET"
    [ ! -d "$CMAKE_BUILD_DIR" ] && nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."

    time nx_verbose cmake --build "$CMAKE_BUILD_DIR" "$@"
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

    nx_verbose ctest $TEST_ARG "$@"
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

    if [ -z "$1" ]; then #< No other args - run apidoctool to generate documentation.
        nx_verbose java -jar "$JAR" -verbose code-to-xml -vms-path "$VMS_DIR" \
            -template-xml "$API_TEMPLATE_XML" -output-xml "$API_XML"
    else #< Some args specified - run apidoctool with the specified args.
        nx_verbose java -jar "$JAR" "$@"
    fi
}

build_and_test_nx_kit() # nx_kit_src_dir "$@"
{
    local SRC="$1"; shift
    nx_verbose cmake "$SRC" -GNinja || return $?
    nx_verbose cmake --build . "$@" || return $?
    ./nx_kit_test
}

do_kit() # "$@"
{
    find_VMS_DIR

    # Recreate nx_kit build dir in /tmp.
    local KIT_BUILD_DIR="/tmp/nx_kit-build"
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

build_installer_cmake()
{
    # TODO: Implement.
    nx_fail "NOT IMPLEMENTED: build_installer_cmake()"
}

build_installer_mvn()
{
    local INSTALLER_PROJECT
    case "$TARGET" in
        edge1) INSTALLER_PROJECT="isd";;
        bpi|rpi|bananapi) INSTALLER_PROJECT="rpi";;
        linux|tx1|anrdoir|ios) nx_fail "NOT IMPLEMENTED for box=$TARGET";;
        *) nx_fail "Unsupported target [$TARGET].";;
    esac

    nx_verbose mvn package -Dbox="$BOX" -Darch="$ARCH" --projects :"$INSTALLER_PROJECT"
}

test_installer_tar_gz() # original.tar.gz built.tar.gz
{
    nx_echo "Comparing .tar.gz archives by checksum:"

    # Using "tarsum.py" to produce two columns: md5 and filename for each archive file.
    local ORIGINAL_OUT="/tmp/test-installer-tar-gz-original.txt"
    local BUILT_OUT="/tmp/test-installer-tar-gz-built.txt"
    tarsum.py < "$1" |sort -k 2 >"$ORIGINAL_OUT"
    tarsum.py < "$2" |sort -k 2 >"$BUILT_OUT"

    nx_verbose diff "$ORIGINAL_OUT" "$BUILT_OUT" \
        || nx_fail "Archives are different; see above."

    rm "$ORIGINAL_OUT"
    rm "$BUILT_OUT"
    nx_echo "SUCCESS: The built .tar.gz contains the same files as the original one."
}

test_installer_zip() # original.zip built.zip built.tar.gz
{
    local ORIGINAL_ZIP="$1"
    local BUILT_ZIP="$2"
    local BUILT_TAR_GZ="$3"

    nx_echo "Comparing .zip archives by contents:"

    # Unpack original.zip - do this every time to allow the .zip file to be updated by the user.
    local ORIGINAL_ZIP_DIR="${ORIGINAL_ZIP%.zip}"
    rm -rf "$ORIGINAL_ZIP_DIR"
    mkdir -p "$ORIGINAL_ZIP_DIR"
    unzip -q "$ORIGINAL_ZIP" -d "$ORIGINAL_ZIP_DIR"

    local BUILT_ZIP_FILENAME=$(basename "$BUILT_ZIP")
    local BUILT_ZIP_DIR="$(dirname "$1")/built-${BUILT_ZIP_FILENAME%.zip}"
    rm -rf "$BUILT_ZIP_DIR"
    mkdir -p "BUILT_ZIP_DIR"
    unzip -q "$BUILT_ZIP" -d "$BUILT_ZIP_DIR"

    # Tar.gz in zips are bitwise-different, thus, compare tar.gz in built zip to built tar.gz.
    nx_verbose diff "$BUILT_TAR_GZ" "$BUILT_ZIP_DIR/$(basename "$BUILT_TAR_GZ")" \
        || nx_fail "The .tar.gz archive in .zip differs from the one built."

    nx_verbose diff -r "$ORIGINAL_ZIP_DIR" "$BUILT_ZIP_DIR" --exclude $(basename "$BUILT_TAR_GZ") \
        || nx_fail "The .zip archives are different; see above."

    rm -r "$ORIGINAL_ZIP_DIR"
    rm -r "$BUILT_ZIP_DIR"
    nx_echo "SUCCESS: The built .zip contains the same files as the original one."
}

do_test_installer()
{
    find_VMS_DIR
    get_TARGET "$1" && shift

    local BUILT_TAR_GZ
    local BUILT_ZIP
    if [ "$1" = "mvn" ]; then
        shift
        build_installer_mvn || exit $?
        nx_find_file BUILT_TAR_GZ "$VMS_DIR" '.*nxwitness-.*\.tar\.gz'
        nx_find_file BUILT_ZIP "$VMS_DIR" '.*nxwitness-.*\.zip'
    else
        get_CMAKE_BUILD_DIR "$TARGET"
        if [ ! -d "$CMAKE_BUILD_DIR" ]; then
            nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."
        fi
        build_installer_cmake || exit $?
        nx_find_file BUILT_TAR_GZ "$CMAKE_BUILD_DIR" '.*nxwitness-.*\.tar\.gz'
        nx_find_file BUILT_ZIP "$CMAKE_BUILD_DIR" '.*nxwitness-.*\.zip'
    fi

    nx_echo
    test_installer_tar_gz "$1"/$(basename "$BUILT_TAR_GZ") "$BUILT_TAR_GZ" || exit $?
    nx_echo
    test_installer_zip "$1"/$(basename "$BUILT_ZIP") "$BUILT_ZIP" "$BUILT_TAR_GZ"
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
        kit-rdep)
            nx_pushd "$PACKAGES_DIR/any/nx_kit"
            rdep -u || exit $?
            nx_echo "SUCCESS: nx_kit uploaded via rdep"
            nx_popd
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
            do_gen "$@" && do_build "$1"
            ;;
        test-installer)
            do_test_installer "$@"
            ;;
        print-dirs)
            find_VMS_DIR
            get_TARGET "$1" && shift
            get_CMAKE_BUILD_DIR "$TARGET"
            if [ ! -d "$CMAKE_BUILD_DIR" ]; then
                nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."
            fi
            echo "$VMS_DIR"
            echo "$CMAKE_BUILD_DIR"
            ;;
        tunnel) # ip1 [ip2]...
            local SUBNET="10.0."
            local SELF_IP=$(ifconfig |awk '/inet addr/{print substr($2,6)}' |grep "$SUBNET")
            local ID=${SELF_IP##*.} #< Take the last byte of SELF_IP.
            [ "$*" = "" ] && nx_fail "List of host IP addresses not specified."
            local HOSTS_ARGS=""
            local PORT_PREFIX=22
            for IP in "$@"; do
                nx_echo "Tunnelling $IP as localhost:$PORT_PREFIX$ID"
                HOSTS_ARG="$HOSTS_ARG -L$PORT_PREFIX$ID:$IP:22"
                ((PORT_PREFIX+=1))
            done

            nx_verbose ssh$HOSTS_ARG -R22$ID:localhost:22 $LA_HDW_MX_USER@la.hdw.mx
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
