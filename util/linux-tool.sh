#!/bin/bash
set -o pipefail

source "$(dirname $0)/utils.sh"

nx_load_config "${RC=".linux-toolrc"}"
: ${VMS_DIR=""} #< nx_vms repo.
: ${TARGET=""} #< Target; "linux" for desktop Linux. If empty on Linux, VMS_DIR name is analyzed.
: ${CONFIG="Debug"} #< Build configuration - either "Debug" or "Release".
: ${DISTRIB=0} #< 0|1 - enable/disable building with distributions.
: ${CUSTOMIZATION=""}
: ${DEVELOP_DIR="$HOME/develop"}
: ${WIN_DEVELOP_DIR="/C/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages"}
: ${WINDOWS_QT_DIR="$PACKAGES_DIR/windows-x64/qt-5.6.1-1"}
: ${LINUX_QT_DIR="$PACKAGES_DIR/linux-x64/qt-5.6.2-2"}
: ${BUILD_DIR=""} #< If empty, will be detected based on the VMS_DIR name and the target.
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the cmake build dir.
: ${DEV=1} #< Whether to make a developer build: -DdeveloperBuild=ON|OFF.
if nx_is_cygwin
then
    : ${CMAKE_GEN=""}
else
    : ${CMAKE_GEN="Ninja"}
fi
: ${NX_KIT_DIR="open/artifacts/nx_kit"} #< Path inside "nx_vms".
: ${SSH_MEDIATOR_HOST="la.hdw.mx"}
: ${SSH_MEDIATOR_USER="$USER"}
: ${TUNNEL_BACKGROUND_RRGGBB="600000"}
: ${TUNNEL_S_DEFAULT_PORT=7001}
: ${TUNNEL_SELF_IP_SUBNET_PREFIX="10\\.0\\."}
: ${TESTCAMERA_SELF_IP_SUBNET_PREFIX="192\\.168\\."}
: ${TEMP_DIR="$(dirname $(mktemp `# dry run #` -u))"}
if nx_is_cygwin
then
    : ${INI_FILES_DIR=$(cygpath -u "$LOCALAPPDATA/nx_ini")}
else
    : ${INI_FILES_DIR="$HOME/.config/nx_ini"}
fi
: ${NINJA_CLEAN_TOOL="$(dirname "$0")/../ninja_clean/ninja_clean.py"}

#--------------------------------------------------------------------------------------------------

help_callback()
{
    cat \
<<EOF
Swiss Army Knife for Linux: execute various commands.
Use ~/$RC to override workstation-dependent environment vars (see them in this script).
Usage: run from any dir inside the proper nx_vms dir:

 $(basename "$0") <options> <command>

$NX_HELP_TEXT_OPTIONS

Here <command> can be one of the following:

 ini # Create empty .ini files in $INI_FILES_DIR (to be filled with defauls).

 apidoc dev|prod [<action>|run] [args] # Run apidoctool from devtools or packages/any.
 apidoc-rdep # Run apidoctool tests, deploy from devtools to packages/any and upload via "rdep -u".

 kit [cygwin] [keep-build-dir] [cmake-build-args] # $NX_KIT_DIR: build, test.
 kit-rdep # Upload $PACKAGES_DIR/any/nx_kit via "rdep -u".

 start-s [args] # Start mediaserver with [args].
 stop-s # Stop mediaserver.
 start-c [args] # Start desktop_client with [args].
 stop-c # Stop desktop_client.
 run-ut [all|test_name] [args] # Run all or the specified unit test via ctest.
 testcamera [video-file.ext] [args] # Start testcamera, or show its help.

 dmp file.dmp [args] # Cygwin-only: Analyze .dmp with crash_analyzer. Requires win-python3.

 share target_dir [branch] # Do hg share, update and copy ".hg/hgrc". Default branch is target_dir.
 cd # Change current dir: source dir <-> build dir.
 gen [cache] [cmake-args] # Perform cmake generation.
 build # Build via "cmake --build <dir>".
 cmake [gen-args] # Perform cmake generation, then build via "cmake --build".
 distrib # Build distribution.
 test-distrib [checksum] [no-build] orig/archives/dir # Test if built matches orig.

 repos # List all hg repos in DEVELOP_DIR with their branches.
 print-dirs # Print VMS_DIR and BUILD_DIR for the target, on separate lines.
 tunnel ip1 [ip2]... # Create two-way ssh tunnel to Burbank for the specified Burbank IP addresses.
 tunnel-s ip1 [port]... # Create ssh tunnel to Burbank for the specified port (default is 7001).
EOF
}

#--------------------------------------------------------------------------------------------------

# [out] TARGET
# [out] CUSTOMIZATION
# [out] QT_DIR
# [in] VMS_DIR
get_TARGET_and_CUSTOMIZATION_and_QT_DIR()
{
    if [ -z "$TARGET" ]
    then
        if nx_is_cygwin
        then
            TARGET="windows"
        else
            # Trying auto-detect from VMS_DIR being "*-target".
            TARGET="linux"
            if [[ $VMS_DIR =~ ^.+-([^-]+)$ ]]
            then
                local -r SUFFIX="${BASH_REMATCH[1]}"
                case "$SUFFIX" in
                    windows|linux|tx1|bpi|rpi|bananapi|android-arm|edge1) TARGET="$SUFFIX";;
                    *) `# Suffix is not a recognized target, ignore it. #`;;
                esac
            fi
        fi
    fi

    # If the target is already defined, use its value.

    case "$TARGET" in
        windows) QT_DIR="$WINDOWS_QT_DIR";;
        linux) QT_DIR="$LINUX_QT_DIR";;
        tx1|bpi|rpi|bananapi|android-arm) `# Do nothing #`;;
        edge1) CUSTOMIZATION="digitalwatchdog";;
        "") nx_fail "Unknown target - either set TARGET, or use build dir suffix \"-target\".";;
        *) nx_fail "Target \"$TARGET\" is not supported.";;
    esac

    # Assertion: target "windows" is supported only in cygwin.
    if nx_is_cygwin
    then
        if [ "$TARGET" != "windows" ]
        then
            nx_fail "On Windows, only \"windows\" target is supported, but \"$TARGET\" detected."
        fi
    else
        if [ "$TARGET" = "windows" ]
        then
            nx_fail "On Linux, \"windows\" target is not supported."
        fi
    fi
}

###
 # Deduce CMake build dir out of VMS_DIR and TARGET. Examples:
 # nx -> nx-build-isd
 # nx-bpi -> nx-bpi-build.
 # /C/develop/nx -> nx-win-build-linux
 # [in] VMS_DIR
 ##
get_BUILD_DIR()
{
    if [ ! -z "${BUILD_DIR:+x}" ]
    then #< BUILD_DIR is defined and not empty.
        return 0
    fi

    case "$TARGET" in
        windows|linux) local -r TARGET_SUFFIX="";;
        *) local -r TARGET_SUFFIX="-$TARGET";;
    esac

    case "$VMS_DIR" in
        *"$TARGET_SUFFIX")
            BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
            ;;
        "$WIN_DEVELOP_DIR"/*)
            local -r VMS_DIR_NAME=${VMS_DIR#$WIN_DEVELOP_DIR/} #< Removing the prefix.
            BUILD_DIR="$DEVELOP_DIR/$VMS_DIR_NAME-win$BUILD_SUFFIX$TARGET_SUFFIX"
            ;;
        *)
            BUILD_DIR="$VMS_DIR$BUILD_SUFFIX$TARGET_SUFFIX"
            ;;
    esac
}

# Convert VMS_DIR path to start with DEVELOP_DIR, if it's different due to symlinks.
canonicalize_VMS_DIR()
{
    # NOTE: In Cygwin, path in CMakeCache.txt is like "C:/develop/...".
    local -r VMS_DIR_ABSOLUTE=$(nx_absolute_path "$(nx_unix_path "$VMS_DIR")")
    local -r DEVELOP_DIR_ABSOLUTE=$(nx_absolute_path "$DEVELOP_DIR")

    if [[ $VMS_DIR_ABSOLUTE =~ ^$DEVELOP_DIR_ABSOLUTE ]]
    then
        VMS_DIR="$DEVELOP_DIR${VMS_DIR_ABSOLUTE#$DEVELOP_DIR_ABSOLUTE}"
    else
        VMS_DIR="$VMS_DIR_ABSOLUTE"
    fi
}

# Extract the specified variable value from CMakeCache.txt. Print nothing if CMakeCache.txt does
# not exist (then return 2), or the variable is not found (then return 1) or has empty value (then
# return 0).
printCmakeCacheValue() # cmake_build_dir cmake_var_name
{
    local -r CMAKE_BUILD_DIR="$1" && shift
    local -r CMAKE_VAR_NAME="$1" && shift

    local -r CMAKE_CACHE_TXT="$CMAKE_BUILD_DIR/CMakeCache.txt"
    if [ ! -f "$CMAKE_CACHE_TXT" ]
    then
        return 2
    fi

    cat "$CMAKE_CACHE_TXT" |grep "$CMAKE_VAR_NAME:" |tr -d "\r" `#< Needed on cygwin. #` \
        |awk 'BEGIN { FS="=" }; { print $2 }'
    return 0
}

# Determine value of common variables, including current repository directory: scan from the
# current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
# [in] DEVELOP_DIR
# [out] TARGET
# [out] BUILD_DIR
setup_vars()
{
    local -r HELP="Run this script from any dir inside a vms repo dir or its cmake build dir."
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" "$HELP"
    local -r CMAKE_CACHE_TXT="$VMS_DIR/CMakeCache.txt"
    local -r CMAKE_LISTS_TXT="$VMS_DIR/CMakeLists.txt"

    if [[ ! -f "$CMAKE_CACHE_TXT" && ! -f "$CMAKE_LISTS_TXT" && $VMS_DIR =~ $BUILD_SUFFIX$ ]]
    then #< Assume a cmake build dir without CMakeCache.txt: guess VMS_DIR by removing the suffix.
        BUILD_DIR="$VMS_DIR"
        VMS_DIR=${VMS_DIR%$BUILD_SUFFIX}
        local -r ACTUAL_CMAKE_LISTS_TXT="$VMS_DIR/CMakeLists.txt"
        if [ ! -f "$ACTUAL_CMAKE_LISTS_TXT" ]
        then
            nx_fail "Cannot find $ACTUAL_CMAKE_LISTS_TXT" "$HELP"
        fi
        get_TARGET_and_CUSTOMIZATION_and_QT_DIR
    elif [ -f "$CMAKE_CACHE_TXT" ]
    then #< This is a cmake build dir: find respective repo dir via CMakeCache.txt.
        BUILD_DIR="$VMS_DIR"
        VMS_DIR=$(printCmakeCacheValue "$VMS_DIR" CMAKE_HOME_DIRECTORY)
        if [ -z "VMS_DIR" ]
        then
            nx_fail "CMAKE_HOME_DIRECTORY not found in $CMAKE_CACHE_TXT" "$HELP"
        fi
        canonicalize_VMS_DIR
        get_TARGET_and_CUSTOMIZATION_and_QT_DIR
    else #< This is not a cmake build dir: test it to be vms project repo dir.
        if [ ! -f "$CMAKE_LISTS_TXT" ]
        then
            nx_fail "Cannot find $CMAKE_LISTS_TXT" "$HELP"
        fi

        if ! grep "project(vms " "$CMAKE_LISTS_TXT" >/dev/null
        then
            nx_fail "The parent repo is not \"vms\" project." "$HELP"
        fi

        get_TARGET_and_CUSTOMIZATION_and_QT_DIR
        get_BUILD_DIR
    fi

    case "$CONFIG" in
        Release|Debug);;
        *) nx_fail "Invalid build configuration in \$CONFIG: [$CONFIG].";;
    esac
}

do_share() # target_path [branch]
{
    if (( $# >= 1 ))
    then
        local -r TARGET_PATH="$1" && shift
    else
        nx_fail "Target path should be specified as the first arg."
    fi

    if (( $# >= 1 ))
    then
        local -r BRANCH="$1" && shift
    else
        local -r BRANCH=$(basename "$TARGET_PATH")
    fi

    # Determine TARGET_DIR.
    if [[ $TARGET_PATH != /* ]]
    then #< The path is relative, treat as relative to VMS_DIR parent.
        local -r TARGET_DIR="$VMS_DIR/../$TARGET_PATH"
    else #< The path is absolute: use as is.
        local -r TARGET_DIR="$TARGET_PATH"
    fi
    if [[ -d $TARGET_DIR ]]
    then
        nx_fail "Target dir already exists: $TARGET_DIR"
    fi

    nx_verbose hg share "$(nx_path "$VMS_DIR")" "$(nx_path "$TARGET_DIR")" || return $?
    cd "$TARGET_DIR" || return $?
    nx_verbose hg update "$BRANCH" || return $?
    nx_verbose cp "$VMS_DIR/.hg/hgrc" "$TARGET_DIR/.hg/" || return $?
}

do_gen() # [cache] "$@"
{
    nx_cd "$VMS_DIR"

    case "$CONFIG" in
        Release) local -r CONFIG_ARG="-DCMAKE_BUILD_TYPE=$CONFIG";;
        Debug) local -r CONFIG_ARG="";;
    esac

    local -i CACHE_ARG=0
    if [[ $# -ge 1 && $1 = "cache" ]]
    then
        shift
        CACHE_ARG=1
    fi

    if [ -d "$BUILD_DIR" ]
    then
        nx_echo "WARNING: Dir $BUILD_DIR already exists."
        if [ $CACHE_ARG = 0 ]
        then
            local -r CMAKE_CACHE="$BUILD_DIR/CMakeCache.txt"
            if [ -f "$CMAKE_CACHE" ]
            then
                nx_verbose rm "$CMAKE_CACHE"
            fi
        fi
    fi
    mkdir -p "$BUILD_DIR"

    nx_pushd "$BUILD_DIR"
    nx_echo "+ cd \"$BUILD_DIR\"" #< Log "cd build-dir".
    case "$TARGET" in
        linux) local -r TARGET_ARG="";;
        windows) local -r TARGET_ARG="-Ax64 -Thost=x64";;
        *) local -r TARGET_ARG="-DtargetDevice=$TARGET";;
    esac

    local GENERATOR_ARG=""
    if [ ! -z "$CMAKE_GEN" ]
    then
        GENERATOR_ARG="-G$CMAKE_GEN"
    fi

    local CUSTOMIZATION_ARG=""
    [ ! -z "$CUSTOMIZATION" ] && CUSTOMIZATION_ARG="-Dcustomization=$CUSTOMIZATION"

    local DISTRIB_ARG=""
    [[ $DISTRIB = 1 ]] && DISTRIB_ARG="-DwithDistributions=ON"

    local DEV_ARG=""
    [[ $DEV = 0 ]] && DEV_ARG="-DdeveloperBuild=OFF"

    nx_verbose cmake "$(nx_path "$VMS_DIR")" \
        -DCMAKE_C_COMPILER_WORKS=1 -DCMAKE_CXX_COMPILER_WORKS=1 \
        ${GENERATOR_ARG:+"$GENERATOR_ARG"} \
        $CUSTOMIZATION_ARG $TARGET_ARG $CONFIG_ARG $DISTRIB_ARG $DEV_ARG "$@"
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_build()
{
    if [ ! -d "$BUILD_DIR" ]
    then
        nx_fail "Dir $BUILD_DIR does not exist, run cmake generation first."
    fi

    if [ "$TARGET" = "windows" ]
    then
        case "$CONFIG" in
            Release) local -r CONFIG_ARG="--config $CONFIG";;
            Debug) local -r CONFIG_ARG="";;
        esac
    else
        local -r CONFIG_ARG=""
    fi

    nx_cd "$VMS_DIR"
    time nx_verbose cmake --build "$(nx_path "$BUILD_DIR")" $CONFIG_ARG "$@"
}

do_run_ut() # [all|TestName] "$@"
{
    nx_verbose cd "$BUILD_DIR"

    local TEST_NAME="$1" && shift

    local TEST_ARG
    case "$TEST_NAME" in
        all) TEST_ARG="";;
        "") nx_fail "Expected either 'all' or a test name as the first arg.";;
        *) TEST_ARG="-R $TEST_NAME";;
    esac

    if [ "$TARGET" = "windows" ]
    then
        local -r CONFIG_ARG="-C $CONFIG"
    else
        local -r CONFIG_ARG=""
    fi

    nx_verbose ctest $CONFIG_ARG $TEST_ARG "$@"
}

copy_if_exists_and_different() # source_file target_file
{
    local -r SOURCE_FILE="$1" && shift
    local -r TARGET_FILE="$1" && shift

    if [ -f "$SOURCE_FILE" ] && \
        ( [ ! -f "$TARGET_FILE" ] || ! diff "$SOURCE_FILE" "$TARGET_FILE" >/dev/null )
    then
        nx_echo
        nx_verbose cp "$SOURCE_FILE" "$TARGET_FILE" || exit $?
    fi
}

find_APIDOCTOOL_JAR()
{
    local PACKAGE=$(cat "$VMS_DIR/sync_dependencies.py" \
        |grep -oE '"any/apidoctool(-[0-9.]+)?' |sed 's$"any/$$g')

    if [ -z "$PACKAGE" ]
    then
        PACKAGE="apidoctool"
    fi

    APIDOCTOOL_JAR="$PACKAGES_DIR/any/$PACKAGE/apidoctool.jar"
}

find_APIDOCTOOL_PARAMS()
{
    APIDOCTOOL_PARAMS=( -config "$(nx_path "$VMS_DIR/mediaserver_core/api/apidoctool.properties")" )
    nx_log_array APIDOCTOOL_PARAMS
}

do_apidoc() # dev|prod [action] "$@"
{
    local -r TOOL="$1" && shift
    if [ "$TOOL" = "dev" ]
    then
        local -r JAR=$(nx_path "$DEVELOP_DIR/devtools/apidoctool/out/apidoctool.jar")
    elif [ "$TOOL" = "prod" ]
    then
        local APIDOCTOOL_JAR
        find_APIDOCTOOL_JAR
        local -r JAR=$(nx_path "$APIDOCTOOL_JAR")
    else
        nx_fail "Invalid apidoctool location \"$TOOL\": expected \"dev\" or \"prod\"."
    fi

    if [ $# = 0 ]
    then
        local -r ACTION="code-to-xml"
    else
        local -r ACTION="$1" && shift
    fi

    local -a APIDOCTOOL_PARAMS
    find_APIDOCTOOL_PARAMS

    local -r API_XML="$BUILD_DIR/mediaserver_core/api.xml"
    local -r API_JSON="$BUILD_DIR/mediaserver_core/api.json"

    local -r API_TEMPLATE_XML="$VMS_DIR/mediaserver_core/api/api_template.xml"
    if [ ! -f "$API_TEMPLATE_XML" ]
    then
        nx_fail "Cannot open file $API_TEMPLATE_XML"
    fi

    if [ "$ACTION" = "run" ]
    then
        time nx_verbose java -jar "$JAR" "$@"
        RESULT=$?
    else #< Run apidoctool with appropriate args for the action, adding the remaining args, if any.
        local -r OUTPUT_DIR="$TEMP_DIR/apidoctool"
        local -i OUTPUT_DIR_NEEDED=0
        local -r TEST_DIR="$DEVELOP_DIR/devtools/apidoctool/test"
        case "$ACTION" in
            code-to-xml)
                local -r ARGS=(
                    -vms-path "$(nx_path "$VMS_DIR")"
                    -template-xml "$(nx_path "$API_TEMPLATE_XML")"
                    -output-xml $(nx_path "$API_XML")
                    -output-json $(nx_path "$API_JSON")
                    ${APIDOCTOOL_PARAMS[@]}
                )
                ;;
            test)
                OUTPUT_DIR_NEEDED=1
                local -r ARGS=(
                    -test-path "$(nx_path "$TEST_DIR")"
                    -output-test-path "$(nx_path "$OUTPUT_DIR")"
                    -config "$(nx_path "$TEST_DIR/apidoctool.properties")"
                )
                ;;
            sort-xml)
                OUTPUT_DIR_NEEDED=1
                local -r ARGS=(
                    -group-name "System API"
                    -source-xml $(nx_path "$API_XML")
                    -output-xml "$(nx_path "$OUTPUT_DIR/api.xml")"
                )
                ;;
            print-deps)
                local -r ARGS=( ${APIDOCTOOL_PARAMS[@]} )
                ;;
            *) nx_fail "Unsupported action: [$ACTION]";;
        esac
        if [ $OUTPUT_DIR_NEEDED = 1 ]
        then
            rm -rf "$OUTPUT_DIR"
            nx_verbose mkdir -p "$OUTPUT_DIR" || return $?
        fi
        time nx_verbose java -jar "$JAR" -verbose "$ACTION" "${ARGS[@]}" "$@"
        RESULT=$?
    fi

    copy_if_exists_and_different "$API_XML" \
        "$BUILD_DIR/mediaserver_core/resources/static/api.xml"
    copy_if_exists_and_different "$API_JSON" \
        "$BUILD_DIR/mediaserver_core/resources/static/api.json"

    return $RESULT
}

do_apidoc_rdep() # "$@"
{
    local -r DEV_DIR="$DEVELOP_DIR/devtools/apidoctool"
    local -r JAR_DEV="$DEV_DIR/out/apidoctool.jar"
    local -r PACKAGE_DIR="$PACKAGES_DIR/any/apidoctool-2.0"
    local -r JAR_PROD="$PACKAGE_DIR/apidoctool.jar"
    local -r TEST_DIR="$DEV_DIR/test"
    local -r APIDOC_PROPERTIES="$TEST_DIR/apidoctool.properties"

    local -r OUTPUT_DIR="$TEMP_DIR/apidoctool"
    rm -rf "$OUTPUT_DIR"
    nx_verbose mkdir -p "$OUTPUT_DIR" || return $?

    nx_verbose java -jar "$(nx_path "$JAR_DEV")" \
        -verbose test \
        -test-path "$(nx_path "$TEST_DIR")" \
        -output-test-path "$(nx_path "$OUTPUT_DIR")" \
        -config "$(nx_path "$APIDOC_PROPERTIES")" \
        || exit $?

    nx_echo
    cp "$JAR_DEV" "$JAR_PROD" || exit $?

    nx_pushd "$PACKAGE_DIR"
    rdep -u || exit $?
    nx_echo
    nx_echo "SUCCESS: apidoctool tested and uploaded via rdep"
    nx_popd
}

# [in] MSVC 0|1 Whether to use MSVC (cygwin only).
build_and_test_nx_kit() # nx_kit_src_dir "$@"
{
    local -r SRC="$1" && shift

    if [[ $MSVC = 1 ]]
    then
        local -r GENERATION_ARGS="-Ax64 -Thost=x64"
        local -r GENERATOR_ARG=""
        local -r BUILD_ARGS="--config Release"
        local -r EXE_DIR="Release"
    else
        local -r BUILD_ARGS=""
        local -r EXE_DIR="."
        if nx_is_cygwin
        then
            local -r GENERATION_ARGS="-DCMAKE_C_COMPILER=gcc"
            local -r GENERATOR_ARG="-GUnix Makefiles"
        else
            local -r GENERATION_ARGS=""
            local -r GENERATOR_ARG="-GNinja"
        fi
    fi

    nx_verbose cmake "$SRC" -DCMAKE_BUILD_TYPE=Release \
        ${GENERATOR_ARG:+"$GENERATOR_ARG"} $GENERATION_ARGS "$@" || return $?
    nx_echo
    time nx_verbose cmake --build . $BUILD_ARGS || return $?
    nx_echo
    "$EXE_DIR"/nx_kit_*
}

do_kit() # "$@"
{
    if (( $# >= 1 )) && [[ $1 = "cygwin" ]]
    then
        shift
        if ! nx_is_cygwin
        then
            nx_fail "ERROR: 'cygwin' option is supported only on cygwin."
        fi
        local -r -i MSVC=0
    else
        if nx_is_cygwin
        then
            local -r -i MSVC=1
        else
            local -r -i MSVC=0
        fi
    fi

    if (( $# >= 1 )) && [[ $1 = "keep-build-dir" ]]
    then
        shift
        local -r -i KEEP_BUILD_DIR=1
    else
        local -r -i KEEP_BUILD_DIR=0
    fi

    # Recreate nx_kit build dir in $TEMP_DIR.
    local KIT_BUILD_DIR="$TEMP_DIR/nx_kit-build"
    rm -rf "$KIT_BUILD_DIR"
    mkdir -p "$KIT_BUILD_DIR" || return $?
    nx_pushd "$KIT_BUILD_DIR"
    nx_echo "+ cd $KIT_BUILD_DIR"

    local KIT_SRC_DIR="$VMS_DIR/$NX_KIT_DIR"
    build_and_test_nx_kit "$KIT_SRC_DIR" "$@" || { local RESULT=$?; nx_popd; return $?; }

    nx_popd
    if [[ $KEEP_BUILD_DIR = 0 ]]
    then
        rm -rf "$KIT_BUILD_DIR"
        nx_echo "Built successfully."
    else
        nx_echo
        nx_echo "ATTENTION: Built at $KIT_BUILD_DIR"
        #nx_echo
    fi

    # Deploying to artifacts commented out - starting with vms_3.2, this artifact is not used.
    #nx_verbose rm -r "$PACKAGES_DIR/any/nx_kit/src"
    #nx_verbose cp -r "$KIT_SRC_DIR/src" "$PACKAGES_DIR/any/nx_kit/" || return $?
    #nx_verbose cp -r "$KIT_SRC_DIR/nx_kit.cmake" "$PACKAGES_DIR/any/nx_kit/" || return $?
    #nx_echo
    #nx_echo "SUCCESS: $NX_KIT_DIR/src and nx_kit.cmake copied to packages/any/"
}

log_build_vars()
{
    local MESSAGE="+"
    [[ $TARGET != windows ]] && MESSAGE+=" TARGET=$TARGET"
    MESSAGE+=" CONFIG=$CONFIG"
    [[ $DISTRIB = 1 ]] && MESSAGE+=" DISTRIB=$DISTRIB"

    echo "$MESSAGE"
}

do_cmake() # "$@"
{
    do_gen "$@" || return $?

    if ! nx_is_cygwin && [[ -f $BUILD_DIR/known_files.txt ]]
    then
        ( cd "$BUILD_DIR"
            nx_verbose "$NINJA_CLEAN_TOOL"
        ) || return $?
    fi

    do_build
}

build_distrib() # "$@"
{
    do_cmake -DwithDistributions=ON "$@"
}

list_tar_gz() # CHECKSUM archive.tar.gz listing.txt
{
    local -r -i CHECKSUM="$1" && shift
    local -r ARCHIVE="$1" && shift
    local -r LISTING="$1" && shift

    if [ $CHECKSUM = 1 ]
    then
        # Using "tarsum.py" to produce two columns for each archive file: md5, filename.
        tarsum.py <"$ARCHIVE" |sort -k 2 >"$LISTING" \
            || nx_fail "tarsum.py failed, see above."
    else
        # tar output: 1-permissions, 2-user/group, 3-size, 4-date, 5-time, filename...
        tar tvf "$ARCHIVE" \
            |awk '{$1=$2=$3=$4=$5=""; gsub("^ +", "", $0); print $0}' \
            |sort >"$LISTING" \
            || nx_fail "tar failed, see above."
    fi
}

list_dir() # dir listing.txt
{
    local -r DIR="$1" && shift
    local -r LISTING=$(nx_absolute_path "$1") && shift

    nx_pushd "$DIR"

    find . -exec stat -c '%A %F %g %u %n' {} \; >"$LISTING" \
        || nx_fail "Unable to create file tree listing for directory: $DIR"

    nx_popd
}

compare_distrib_tar_gz() # CHECKSUM original.tar.gz built.tar.gz
{
    local -r -i CHECKSUM="$1" && shift
    local -r ORIGINAL_TAR_GZ="$1" && shift
    local -r BUILT_TAR_GZ="$1" && shift

    if [ $CHECKSUM = 1 ]
    then
        local -r CHECKSUM_MESSAGE="by checksum"
    else
        local -r CHECKSUM_MESSAGE="by filename list"
    fi
    nx_echo "Comparing .tar.gz archives ${CHECKSUM_MESSAGE}:"

    local -r ORIGINAL_LISTING="$ORIGINAL_TAR_GZ.txt"
    local -r BUILT_LISTING="$ORIGINAL_TAR_GZ.BUILT.txt"
    list_tar_gz $CHECKSUM "$ORIGINAL_TAR_GZ" "$ORIGINAL_LISTING"
    list_tar_gz $CHECKSUM "$BUILT_TAR_GZ" "$BUILT_LISTING"

    nx_diff "$ORIGINAL_LISTING" "$BUILT_LISTING" \
        || nx_fail "Archives are different; see above."

    rm "$ORIGINAL_LISTING"
    rm "$BUILT_LISTING"

    nx_echo "SUCCESS: The built .tar.gz contains the same files as the original one."
}

# @param built-inner-file Full path to a file which should be packed inside the archive. It is
#     excluded in .zip contents comparison, but such file inside .zip is compared to the specified
#     file.
#
compare_distrib_zip_with_inner_file() # original.zip built.zip built-inner-file
{
    local -r ORIGINAL_ZIP="$1" && shift
    local -r BUILT_ZIP="$1" && shift
    local -r BUILT_INNER_FILE="$1" && shift

    local -r BUILT_INNER_FILE_EXT=$(nx_file_ext "$BUILT_INNER_FILE")

    nx_echo "Comparing .zip archives (.$BUILT_INNER_FILE_EXT compared to the one built):"

    local DIR

    # Unpack original.zip - do this every time to allow the .zip file to be updated by the user.
    nx_unpack_archive_DIR "$ORIGINAL_ZIP"
    local -r ORIGINAL_ZIP_UNPACKED="$DIR"

    nx_unpack_archive_DIR "$BUILT_ZIP" "${ORIGINAL_ZIP%.zip}.BUILT"
    local -r BUILT_ZIP_UNPACKED="$DIR"

    local -r INNER_FILE_NAME=$(basename "$BUILT_INNER_FILE")

    # Inner files can be bitwise-different, thus, compare the built file to the file in built zip.
    nx_diff "$BUILT_INNER_FILE" "$BUILT_ZIP_UNPACKED/$(basename "$BUILT_INNER_FILE")" \
        || nx_fail "The .$BUILT_INNER_FILE_EXT in .zip differs from the one built."

    nx_diff -r "$ORIGINAL_ZIP_UNPACKED" "$BUILT_ZIP_UNPACKED" \
        --exclude "$INNER_FILE_NAME" \
        || nx_fail "The .zip archives are different; see above."

    # Check that files in .zip have the same permissions.
    local -r ORIGINAL_LISTING="$ORIGINAL_ZIP_UNPACKED.txt"
    local -r BUILT_LISTING="$BUILT_ZIP_UNPACKED.txt"
    list_dir "$ORIGINAL_ZIP_UNPACKED" "$ORIGINAL_LISTING"
    list_dir "$BUILT_ZIP_UNPACKED" "$BUILT_LISTING"
    nx_diff "$ORIGINAL_LISTING" "$BUILT_LISTING" \
        || nx_fail "The .zip  archive file trees are different; see above."

    rm -r "$ORIGINAL_ZIP_UNPACKED"
    rm -r "$BUILT_ZIP_UNPACKED"
    rm "$ORIGINAL_LISTING"
    rm "$BUILT_LISTING"

    nx_echo "SUCCESS:" \
        "The built .zip contains correct .$BUILT_INNER_FILE_EXT, and other files equal originals."
}

compare_distrib_archives() # CHECKSUM original-archive built-archive
{
    local -r -i CHECKSUM="$1" && shift
    local -r ORIGINAL_ARCHIVE="$1" && shift
    local -r BUILT_ARCHIVE="$1" && shift

    local -r EXT=$(nx_file_ext "$ORIGINAL_ARCHIVE")

    nx_echo "Comparing .$EXT archives:"

    local DIR

    # Unpack original - do this every time to allow the archive file to be updated by the user.
    nx_unpack_archive_DIR "$ORIGINAL_ARCHIVE"
    local -r ORIGINAL_UNPACKED="$DIR"

    nx_unpack_archive_DIR "$BUILT_ARCHIVE" "$ORIGINAL_UNPACKED.BUILT"
    local -r BUILT_UNPACKED="$DIR"

    if [ $CHECKSUM = 1 ]
    then
        nx_diff -r "$ORIGINAL_UNPACKED" "$BUILT_UNPACKED" \
            || nx_fail "The .$EXT archives are different; see above."
    fi

    # Compare file trees anyway because `diff -r` does not compare permissions.
    local -r ORIGINAL_LISTING="$ORIGINAL_UNPACKED.txt"
    local -r BUILT_LISTING="$BUILT_UNPACKED.txt"
    list_dir "$ORIGINAL_UNPACKED" "$ORIGINAL_LISTING"
    list_dir "$BUILT_UNPACKED" "$BUILT_LISTING"
    nx_diff "$ORIGINAL_LISTING" "$BUILT_LISTING" \
        || nx_fail "The .$EXT archive file trees are different; see above."

    rm -r "$ORIGINAL_UNPACKED"
    rm -r "$BUILT_UNPACKED"
    rm "$ORIGINAL_LISTING"
    rm "$BUILT_LISTING"

    nx_echo "SUCCESS: The built .$EXT archive files equal originals."
}

# Test .tar.gz-based distribution.
#
# [in] CHECKSUM 0|1
# [in] ORIGINAL_DIR
#
test_distrib_archives()
{
    local -r TAR_GZ_MASK="nxwitness-*.tar.gz"
    local -r ZIP_MASK="nxwitness-*_update*.zip"
    local -r DEBUG_TAR_GZ_SUFFIX="-debug-symbols.tar.gz"

    local BUILT_TAR_GZ
    nx_find_file BUILT_TAR_GZ "main .tar.gz installer" "$BUILD_DIR" -name "$TAR_GZ_MASK" \
        ! -name "*$DEBUG_TAR_GZ_SUFFIX"

    local BUILT_ZIP
    nx_find_file BUILT_ZIP "installer .zip" "$BUILD_DIR" -name "$ZIP_MASK"

    local -r ORIGINAL_TAR_GZ="$ORIGINAL_DIR"/$(basename "$BUILT_TAR_GZ")

    # Test main distrib .tar.gz.
    nx_echo
    compare_distrib_tar_gz $CHECKSUM "$ORIGINAL_TAR_GZ" "$BUILT_TAR_GZ"

    # Test the archive with debug libraries, if its sample is present in the "original" dir.
    local -r ORIGINAL_DEBUG_TAR_GZ="$ORIGINAL_TAR_GZ$DEBUG_TAR_GZ_SUFFIX"
    local -r BUILT_DEBUG_TAR_GZ="$BUILT_TAR_GZ$DEBUG_TAR_GZ_SUFFIX"
    if [ -f "$ORIGINAL_DEBUG_TAR_GZ" ]
    then
        nx_echo
        compare_distrib_tar_gz $CHECKSUM "$ORIGINAL_DEBUG_TAR_GZ" "$BUILT_DEBUG_TAR_GZ"
    else
        # There is no original debug archive - require that there is no such file built.
        if [ -f "$BUILT_DEBUG_TAR_GZ" ]
        then
            nx_fail "Debug symbols archive was built but not expected - the original is absent."
        fi
    fi

    # Test .zip which contains .tar.gz and some other files.
    local -r ORIGINAL_ZIP="$ORIGINAL_DIR"/$(basename "$BUILT_ZIP")
    nx_echo
    compare_distrib_zip_with_inner_file "$ORIGINAL_ZIP" "$BUILT_ZIP" "$BUILT_TAR_GZ"
}

# [out] FILE
# [in] ORIGINAL_DIR
# [in] BUILD_DIR
find_distrib_FILE() # original|built client|server .ext
{
    local LOCATION="$1" && shift
    local MODULE="$1" && shift
    local EXT="$1" && shift

    if [[ $EXT = ".zip" ]]
    then
        local -r DESCRIPTION="update .zip"
        local -r MASK="*-${MODULE}_update-*.zip"
    elif [[ $EXT = ".deb" ]]
    then
        local -r DESCRIPTION=".deb"
        local -r MASK="*-${MODULE}-*.deb"
    else
        nx_fail "find_distrib_file(): Unsupported extension: $EXT"
    fi

    if [[ $LOCATION = original ]]
    then
        local -r DIR="$ORIGINAL_DIR"
    elif [[ $LOCATION = built ]]
    then
        local -r DIR="$BUILD_DIR"
    else
        nx_fail "find_distrib_file(): Unsupported location: $LOCATION"
    fi

    nx_find_file FILE "$LOCATION $MODULE $DESCRIPTION" "$DIR" -name "$MASK"
}

# Test .deb-based distribution.
#
# [in] CHECKSUM 0|1
# [in] ORIGINAL_DIR
#
test_distrib_debs()
{
    # Distribution structure:
    #
    # nxwitness-client-<version>-<platform>-<suffixes>.deb
    # nxwitness-client_update-<version>-<platform>-<suffixes>.zip
    #
    # nxwitness-server-<version>-<platform>-<suffixes>.deb
    # nxwitness-server_update-<version>-<platform>-<suffixes>.zip
    #     nxwitness-server-<version>-<platform>-<suffixes>.deb

    local ORIGINAL_CLIENT_DEB=""
    nx_find_file_optional ORIGINAL_CLIENT_DEB \
        "original client .deb" "$ORIGINAL_DIR" -name "*-client-*.deb" || true

    local FILE

    if [[ ! -z $ORIGINAL_CLIENT_DEB ]]
    then
        find_distrib_FILE built client .deb && local -r BUILT_CLIENT_DEB="$FILE"
        nx_echo
        compare_distrib_archives $CHECKSUM "$ORIGINAL_CLIENT_DEB" "$FILE"

        find_distrib_FILE original client .zip && local -r ORIGINAL_CLIENT_ZIP="$FILE"
        find_distrib_FILE built client .zip && local -r BUILT_CLIENT_ZIP="$FILE"
        nx_echo
        compare_distrib_archives $CHECKSUM "$ORIGINAL_CLIENT_ZIP" "$BUILT_CLIENT_ZIP"
    else
        nx_echo "WARNING: Client .deb not found in the original dir; ignoring."
    fi

    find_distrib_FILE original server .deb && local -r ORIGINAL_SERVER_DEB="$FILE"
    find_distrib_FILE built server .deb && local -r BUILT_SERVER_DEB="$FILE"
    nx_echo
    compare_distrib_archives $CHECKSUM "$ORIGINAL_SERVER_DEB" "$BUILT_SERVER_DEB"

    find_distrib_FILE original server .zip && local -r ORIGINAL_SERVER_ZIP="$FILE"
    find_distrib_FILE built server .zip && local -r BUILT_SERVER_ZIP="$FILE"
    nx_echo
    compare_distrib_zip_with_inner_file "$ORIGINAL_SERVER_ZIP" "$BUILT_SERVER_ZIP" \
        "$BUILT_SERVER_DEB"
}

do_test_distrib() # [checksum] [no-build] orig/archives/dir
{
    nx_cd "$VMS_DIR"

    local -i CHECKSUM=0; [ "$1" = "checksum" ] && { shift; CHECKSUM=1; }
    local -i NO_BUILD=0; [ "$1" = "no-build" ] && { shift; NO_BUILD=1; }
    local -r ORIGINAL_DIR=$(nx_absolute_path "$1") && shift

    if [ ! -d "$BUILD_DIR" ]
    then
        nx_fail "Dir $BUILD_DIR does not exist, run cmake generation first."
    fi

    if [ $NO_BUILD = 0 ]
    then
        build_distrib || return $?
    fi

    case "$TARGET" in
        linux)
            test_distrib_debs || return $?
            ;;
        tx1|bpi|rpi|bananapi|edge1)
            test_distrib_archives || return $?
            ;;
        *)
            nx_fail "Target \"$TARGET\" is not supported by this command."
            ;;
    esac

    nx_echo
    nx_echo "All tests SUCCEEDED."
}

# Scan current dir for immediate inner dirs which are repos, and extract info about them.
# [out] REPO_TO_BRANCH: map<repo_dir, branch> Names of current branches.
# [out] REPO_TO_EXTRA: map<repo_dir, extra_info_if_any> Extra info to be printed to the user.
scanRepos_REPO_TO_BRANCH_and_REPO_TO_EXTRA()
{
    local REPO
    for REPO in $(find * -maxdepth 2 -path "*/.hg/branch" -printf '%H\n')
    do
        # Check if the repo dir is mounted from a Windows filesystem.
        local WIN_DIR=$(mount |grep "$HOME/develop/$REPO " |awk '{print $1}')
        if [ ! -z "$WIN_DIR" ]
        then
            local EXTRA=""
            local WIN_REPO=$(basename "$WIN_DIR")
            if [ "$WIN_REPO" != "$REPO" ]
            then
                EXTRA=" $WIN_REPO"
            fi
            REPO_TO_EXTRA["$REPO"]="win$EXTRA" #< Add key-value.
        fi

        REPO_TO_BRANCH["$REPO"]=$(cat "$REPO/.hg/branch") #< Add key-value.
    done

    nx_log_map REPO_TO_BRANCH
    nx_log_map REPO_TO_EXTRA
}

# Scan current dir for immediate inner dirs which are cmake-build-dirs.
# [out] REPO_TO_BUILD_DIRS: map<repo_dir, list<cmake_build_dir>>.
# [out] BUILD_DIR_TO_CONFIG: map<cmake_build_dir, Debug|Release>.
# [out] OTHER_DIRS: array<dir> Non-cmake-build-dirs which names start with some repo_dir name.
scanRepos_REPO_TO_BUILD_DIRS_and_BUILD_DIR_TO_CONFIG_and_OTHER_DIRS() # "${REPOS[@]}"
{
    if [[ -z $BUILD_DIR ]]
    then
        local -r MASK="*"
    else
        local -r MASK="* */$BUILD_DIR"
    fi

    local DIR
    for DIR in $MASK
    do
        if [[ ! -d $DIR ]]
        then
            continue
        fi
        nx_log_var DIR

        local CMAKE_SRC_DIR=$(printCmakeCacheValue "$DIR" CMAKE_HOME_DIRECTORY)
        nx_log_var CMAKE_SRC_DIR

        if [[ ! -z $CMAKE_SRC_DIR ]]
        then
            REPO_TO_BUILD_DIRS["$(basename "$CMAKE_SRC_DIR")"]+="$DIR " #< Add value to key.
            local CMAKE_CONFIG=$(printCmakeCacheValue "$DIR" CMAKE_BUILD_TYPE)
            BUILD_DIR_TO_CONFIG["$DIR"]="$CMAKE_CONFIG" #< Add key-value.
        else
            local -i SOME_REPO_IS_PREFIX_TO_DIR=0
            local -i SOME_REPO_IS_EQUAL_TO_DIR=0
            local REPO
            for REPO in "$@"
            do
                if [[ $DIR =~ ^$REPO.+ ]]
                then
                    SOME_REPO_IS_PREFIX_TO_DIR=1
                fi
                if [[ $DIR = $REPO ]]
                then
                    SOME_REPO_IS_EQUAL_TO_DIR=1
                fi
            done

            if [[ $SOME_REPO_IS_PREFIX_TO_DIR = 1 && $SOME_REPO_IS_EQUAL_TO_DIR = 0 ]]
            then
                OTHER_DIRS+=( "$DIR" ) #< Add array item.
            fi
        fi
    done

    nx_log_map REPO_TO_BUILD_DIRS
    nx_log_map BUILD_DIR_TO_CONFIG
    nx_log_array OTHER_DIRS
}

# Check the specified dirs for .hg/sharedpath and add its contents to the map.
# [out] REPO_TO_SHARED_BASE: map<repo_dir, hg_share_base_dir>.
populate_REPO_TO_SHARED_BASE() # "${REPOS[@]}"
{
    local REPO
    for REPO in "${REPOS[@]}"; do
        local HG_SHAREDPATH_FILE="$REPO/.hg/sharedpath"
        if [[ -f $HG_SHAREDPATH_FILE ]]
        then #< This source folder was created using "hg share" from a base source folder.
            local HG_SHAREDPATH=$(dirname "$(cat "$HG_SHAREDPATH_FILE")")
            local SHAREDPATH=$(nx_unix_path "$HG_SHAREDPATH")
            local SHAREDPATH_RELATIVE=${SHAREDPATH#$(nx_absolute_path "$(pwd)")/}
            REPO_TO_SHARED_BASE["$REPO"]="$SHAREDPATH_RELATIVE" #< Add key-value.
        fi
    done

    nx_log_map REPO_TO_SHARED_BASE
}

printRepos()
{
    cd "$DEVELOP_DIR"

    local -A REPO_TO_BRANCH=() #< map<repo_dir, branch>
    local -A REPO_TO_EXTRA=() #< map<repo_dir, extra_info_if_any>
    scanRepos_REPO_TO_BRANCH_and_REPO_TO_EXTRA

    # Set REPOS to sorted list of repos formed of REPO_TO_BRANCH keys.
    IFS=$'\n' eval 'local REPOS=( $(sort <<<"${!REPO_TO_BRANCH[*]}") )'
    nx_log_array REPOS

    local -A REPO_TO_BUILD_DIRS=() #< map<repo_dir, list<cmake_build_dir>>
    local -A BUILD_DIR_TO_CONFIG=() #< map<cmake_build_dir, build_configuration>.
    local OTHER_DIRS=() #< Mon-cmake-build-dirs which names start with any repo name.
    scanRepos_REPO_TO_BUILD_DIRS_and_BUILD_DIR_TO_CONFIG_and_OTHER_DIRS "${REPOS[@]}"

    local -A REPO_TO_SHARED_BASE=() #< map<repo_dir, hg_share_base_dir>
    populate_REPO_TO_SHARED_BASE "${REPOS[@]}"

    # Print repo dirs.
    for REPO in "${REPOS[@]}"
    do
        local BUILD_DIR_STR=""
        if [ "${REPO_TO_BUILD_DIRS[$REPO]+is_set}" ]
        then
            local DIRS=( ${REPO_TO_BUILD_DIRS[$REPO]} ) #< Split by spaces into array.
            local DIR
            BUILD_DIR_STR=" $(nx_dcyan)=>"
            if [[ ${#DIRS[@]} = 1 ]]
            then
                DIR="${DIRS[0]}"
                local CONFIG_STR="$(nx_lcyan)${BUILD_DIR_TO_CONFIG["$DIR"]::1} "
                BUILD_DIR_STR+=" $CONFIG_STR$(nx_lgreen)$DIR"
            else
                BUILD_DIR_STR+=$'\n    '
                for DIR in "${DIRS[@]}"
                do
                    local CONFIG_STR="$(nx_lcyan)${BUILD_DIR_TO_CONFIG["$DIR"]::1} "
                    BUILD_DIR_STR+="$CONFIG_STR$(nx_lgreen)$DIR"$'\n    '
                done
            fi
        fi

        local EXTRA_STR=""
        if [ "${REPO_TO_EXTRA[$REPO]+is_set}" ]
        then
            EXTRA_STR=" $(nx_lgray)[${REPO_TO_EXTRA["$REPO"]}]"
        fi

        local SHARED_BASE_STR=""
        if [ "${REPO_TO_SHARED_BASE["$REPO"]+is_set}" ]
        then
            SHARED_BASE_STR="$(nx_dcyan)($(nx_lgray)${REPO_TO_SHARED_BASE["$REPO"]}$(nx_dcyan))"
        fi

        nx_echo "$(nx_white)$REPO$SHARED_BASE_STR$EXTRA_STR$BUILD_DIR_STR$(nx_dcyan):" \
            "$(nx_lyellow)${REPO_TO_BRANCH[$REPO]}$(nx_nocolor)"
    done

    # Print other dirs.
    for DIR in "${OTHER_DIRS[@]}"
    do
        nx_echo "$(nx_lred)$DIR$(nx_nocolor)"
    done
}

#--------------------------------------------------------------------------------------------------

main()
{
    TIMEFORMAT="Time taken: %1lR" #< Output for "time" command. Example: 2m12s

    local -r COMMAND="$1" && shift
    case "$COMMAND" in
        apidoc|kit|start-s|start-c|run-ut|testcamera| \
        share|gen|cd|build|cmake|distrib|test-distrib| \
        print-dirs)
            setup_vars
            ;;
    esac

    case "$COMMAND" in
        ini)
            touch "$INI_FILES_DIR"/nx_network.ini
            touch "$INI_FILES_DIR"/nx_network_debug.ini
            touch "$INI_FILES_DIR"/mobile_client.ini
            touch "$INI_FILES_DIR"/appserver2.ini
            touch "$INI_FILES_DIR"/nx_media.ini
            touch "$INI_FILES_DIR"/nx_streaming.ini
            touch "$INI_FILES_DIR"/plugins.ini
            ;;
        #..........................................................................................
        apidoc)
            do_apidoc "$@"
            ;;
        apidoc-rdep)
            do_apidoc_rdep "$@"
            ;;
        #..........................................................................................
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
            nx_verbose cd "$BUILD_DIR"
            case "$TARGET" in
                windows)
                    local -r QT_PATH="$QT_DIR/bin"
                    nx_echo "+ PATH=\"$QT_PATH:\$PATH\""
                    PATH="$QT_PATH:$PATH"
                    nx_verbose bin/mediaserver -e "$@"
                    ;;
                linux)
                    sudo chown root:root bin/root_tool && sudo chmod u+s bin/root_tool
                    nx_verbose bin/mediaserver -e "$@"
                    ;;
                *) nx_fail "Target [$TARGET] not supported yet.";;
            esac
            ;;
        stop-s)
            # TODO: Decide on better impl.
            sudo pkill -9 mediaserver
            ;;
        start-c)
            # TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        stop-c)
            # TODO: Decide on better impl.
            sudo pkill -9 desktop_client
            ;;
        run-ut)
            do_run_ut "$@"
            ;;
        testcamera)
            local -i SHOW_HELP=0
            if [ "$#" = 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]
            then
                SHOW_HELP=1
            fi

            local VIDEO_FILE="$1" && shift

            local -r TEST_CAMERA_BIN="$BUILD_DIR/bin/testcamera"

            if nx_is_cygwin
            then
                PATH="$QT_DIR\bin:$BUILD_DIR/bin:$PATH"
            fi

            if [ $SHOW_HELP = 1 ]
            then
                "$TEST_CAMERA_BIN" || true
            else
                local SELF_IP
                nx_get_SELF_IP "$TESTCAMERA_SELF_IP_SUBNET_PREFIX"
                nx_verbose "$TEST_CAMERA_BIN" --local-interface="$SELF_IP" "$@" \
                    "files=\"$(nx_path "$VIDEO_FILE")\";count=1"
            fi
            ;;
        #..........................................................................................
        dmp)
            if ! nx_is_cygwin
            then
                nx_fail "This command supported only on cygwin."
            fi
            if [ $# -lt 1 ]
            then
                nx_fail "Missing first arg: .dmp file."
            fi
            local -r DMP_FILE="$1" && shift

            nx_verbose win-python3 \
		"$(nx_path "$DEVELOP_DIR/devtools/crash_analyzer/dump_tool.py")" \
                "$(nx_path "$DMP_FILE")" "$@"
            ;;
        #..........................................................................................
        share)
            do_share "$@"
            ;;
        #..........................................................................................
        cd)
            if [[ $(nx_absolute_path "$(pwd)")/ =~ ^$(nx_absolute_path "$VMS_DIR")/ ]]
            then
                echo "$BUILD_DIR"
            elif [[ $(nx_absolute_path "$(pwd)") = $(nx_absolute_path "$BUILD_DIR") ]]
            then
                echo "$VMS_DIR"
            else
                nx_fail "Current dir is neither a cmake build dir nor a vms project dir."
            fi
            ;;
        gen)
            log_build_vars
            do_gen "$@"
            ;;
        build)
            log_build_vars
            do_build "$@"
            ;;
        cmake)
            log_build_vars
            do_cmake "$@"
            ;;
        distrib)
            log_build_vars
            build_distrib "$@"
            ;;
        test-distrib)
            log_build_vars
            do_test_distrib "$@"
            ;;
        #..........................................................................................
        repos)
            printRepos
            ;;
        print-dirs)
            if [ ! -d "$BUILD_DIR" ]
            then
                nx_fail "Dir $BUILD_DIR does not exist, run cmake generation first."
            fi
            echo "$VMS_DIR"
            echo "$BUILD_DIR"
            ;;
        tunnel) # ip1 [ip2]...
            local SELF_IP
            nx_get_SELF_IP "$TUNNEL_SELF_IP_SUBNET_PREFIX"
            local -i -r ID=${SELF_IP##*.} #< Take the last byte of SELF_IP.
            nx_echo "Detected localhost as $SELF_IP, using $ID as port suffix"
            [ "$*" = "" ] && nx_fail "List of host IP addresses not specified."
            local -i -r FWD_PORT=22
            local -i -r BACK_PORT=$FWD_PORT$ID

            local HOSTS_ARGS=""
            local TITLE=""
            local -i PORT_PREFIX=22
            for IP in "$@"
            do
                local -i NEW_PORT=$PORT_PREFIX$ID
                local TUNNEL_DESCRIPTION="localhost:$NEW_PORT->$IP:$FWD_PORT"
                nx_echo "Tunnelling $TUNNEL_DESCRIPTION"
                HOSTS_ARG="$HOSTS_ARG -L$NEW_PORT:$IP:$FWD_PORT"
                TITLE="$TITLE$TUNNEL_DESCRIPTION, "
                ((PORT_PREFIX+=1))
            done
            local -r TUNNEL_BACK_DESCRIPTION="$SSH_MEDIATOR_HOST:$BACK_PORT->localhost:$FWD_PORT"
            echo "Tunnelling $TUNNEL_BACK_DESCRIPTION"
            TITLE="${TITLE}$TUNNEL_BACK_DESCRIPTION"

            nx_push_title
            nx_set_title "$TITLE"
            local OLD_BACKGROUND
            nx_get_background OLD_BACKGROUND
            nx_set_background "$TUNNEL_BACKGROUND_RRGGBB"

            nx_verbose ssh$HOSTS_ARG -R$BACK_PORT:localhost:$FWD_PORT \
                -t "$SSH_MEDIATOR_USER@$SSH_MEDIATOR_HOST" \
                'echo "Press ^C to stop"; sleep infinity'

            nx_set_background "$OLD_BACKGROUND"
            nx_pop_title
            ;;
        tunnel-s) # ip1 [port]
            if [[ $# != 1 && $# != 2 ]]
            then
                nx_fail "Invalid command args."
            fi
            local -r IP="$1"
            if [[ $# = 1 ]]
            then
                local -r -i FWD_PORT="$TUNNEL_S_DEFAULT_PORT"
            else
                local -r -i FWD_PORT="$2"
            fi

            local -r -i PORT_PREFIX=22
            local -r ID=${IP##*.} #< Take the last byte of IP.
            local -r NEW_PORT=$PORT_PREFIX$ID

            local -r TUNNEL_DESCRIPTION="localhost:$NEW_PORT->$IP:$FWD_PORT"
            nx_echo "Tunnelling $TUNNEL_DESCRIPTION"
            nx_push_title
            nx_set_title "$TUNNEL_DESCRIPTION"
            local OLD_BACKGROUND
            nx_get_background OLD_BACKGROUND
            nx_set_background "$TUNNEL_BACKGROUND_RRGGBB"

            nx_verbose ssh -L$NEW_PORT:$IP:$FWD_PORT \
                -t "$SSH_MEDIATOR_USER@$SSH_MEDIATOR_HOST" \
                'echo "Press ^C to stop"; sleep infinity'

            nx_set_background "$OLD_BACKGROUND"
            nx_pop_title
            ;;
        #..........................................................................................
        *)
            nx_fail "Invalid arguments. Run with -h for help."
            ;;
    esac
}

nx_run "$@"
