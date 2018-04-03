#!/bin/bash
set -o pipefail
source "$(dirname $0)/utils.sh"

nx_load_config "${RC=".linux-toolrc"}"
: ${TARGET=""} #< Target; "linux" for desktop Linux. If empty on Linux, VMS_DIR name is analyzed.
: ${CONFIG="Debug"} #< Build configuration - either "Debug" or "Release".
: ${DEVELOP_DIR="$HOME/develop"}
: ${WIN_DEVELOP_DIR="/C/develop"}
: ${PACKAGES_DIR="$DEVELOP_DIR/buildenv/packages"}
: ${WINDOWS_QT_DIR="$PACKAGES_DIR/windows-x64/qt-5.6.1-1"}
: ${LINUX_QT_DIR="$PACKAGES_DIR/linux-x64/qt-5.6.2-2"}
: ${CMAKE_BUILD_DIR=""} #< If empty, will be detected based on the VMS_DIR name and the target.
: ${BUILD_SUFFIX="-build"} #< Suffix to add to "nx_vms" dir to get the cmake build dir.
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
: ${TEMP_DIR="$(dirname $(mktemp `# dry run` -u))"}
: ${CUSTOMIZATION=""}
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

 ini # Create empty .ini files in $TEMP_DIR (to be filled with defauls).

 apidoc [dev|prod] # Run apidoctool from devtools or from packages/any to generate api.xml.
 apidoc-rdep # Run apidoctool tests, deploy from devtools to packages/any and upload via "rdep -u".

 kit [keep-build-dir] [cmake-build-args] # $NX_KIT_DIR: build, test, copy src to artifact.
 kit-rdep # Upload $PACKAGES_DIR/any/nx_kit via "rdep -u".

 start-s [args] # Start mediaserver with [args].
 stop-s # Stop mediaserver.
 start-c [args] # Start desktop_client with [args].
 stop-c # Stop desktop_client.
 run-ut [all|test_name] [args] # Run all or the specified unit test via ctest.
 testcamera [video-file.ext] [args] # Start testcamera, or show its help.

 share target_path # Perform: hg share, update to the current branch and copy ".hg/hgrc".
 gen [cache] [cmake-args] # Perform cmake generation.
 build # Build via "cmake --build <dir>".
 cmake [gen-args] # Perform cmake generation, then build via "cmake --build".
 distrib # Build distribution.
 test-distrib [checksum] [no-build] orig/archives/dir # Test if built matches orig.

 repos # List all hg repos in DEVELOP_DIR with their branches.
 print-dirs # Print VMS_DIR and CMAKE_BUILD_DIR for the target, on separate lines.
 tunnel ip1 [ip2]... # Create two-way ssh tunnel to Burbank for the specified Burbank IP addresses.
 tunnel-s ip1 [port]... # Create ssh tunnel to Burbank for the specified port (default is 7001).
EOF
}

#--------------------------------------------------------------------------------------------------

# [out] TARGET
# [out] CUSTOMIZATION
# [out] QT_DIR
# [in] VMS_DIR
get_TARGET()
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
        if [ "$TARGET" == "windows" ]
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
get_CMAKE_BUILD_DIR()
{
    if [ ! -z "${CMAKE_BUILD_DIR:+x}" ]
    then #< CMAKE_BUILD_DIR is defined and not empty.
        return 0
    fi

    case "$TARGET" in
        windows|linux) local -r TARGET_SUFFIX="";;
        *) local -r TARGET_SUFFIX="-$TARGET";;
    esac

    case "$VMS_DIR" in
        *"$TARGET_SUFFIX")
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX"
            ;;
        "$WIN_DEVELOP_DIR"/*)
            local -r VMS_DIR_NAME=${VMS_DIR#$WIN_DEVELOP_DIR/} #< Removing the prefix.
            CMAKE_BUILD_DIR="$DEVELOP_DIR/$VMS_DIR_NAME-win$BUILD_SUFFIX$TARGET_SUFFIX"
            ;;
        *)
            CMAKE_BUILD_DIR="$VMS_DIR$BUILD_SUFFIX$TARGET_SUFFIX"
            ;;
    esac
}

# Determine value of common variables, including current repository directory: scan from the
# current dir upwards to find root repository dir (e.g. develop/nx_vms).
# [in][out] VMS_DIR
# [in] DEVELOP_DIR
# [out] TARGET
# [out] CMAKE_BUILD_DIR
setup_vars()
{
    nx_find_parent_dir VMS_DIR "$(basename "$DEVELOP_DIR")" \
        "Run this script from any dir inside your nx_vms repo dir."
    get_TARGET
    get_CMAKE_BUILD_DIR

    case "$CONFIG" in
        Release|Debug);;
        *) nx_fail "Invalid build configuration in \$CONFIG: [$CONFIG].";;
    esac
}

do_share() # target_path
{
    setup_vars
    local TARGET_PATH="$1"
    [ -z "$TARGET_PATH" ] && nx_fail "Target path should be specified as the first arg."
    if [[ $TARGET_PATH != /* ]]
    then # The path is relative, treat as relative to VMS_DIR parent.
        local TARGET_DIR="$VMS_DIR/../$TARGET_PATH"
    else # The path is absolute: use as is.
        local TARGET_DIR="$TARGET_PATH"
    fi
    [ -d "$TARGET_DIR" ] && nx_fail "Target dir already exists: $TARGET_DIR"

    local BRANCH=$(hg branch)
    [ -z "$BRANCH" ] && nx_fail "'hg branch' did not provide any output."

    nx_verbose mkdir -p "$TARGET_DIR"
    nx_verbose hg share "$(nx_path "$VMS_DIR")" "$(nx_path "$TARGET_DIR")" || return $?
    nx_verbose cp "$VMS_DIR/.hg/hgrc" "$TARGET_DIR/.hg/" || return $?
    cd "$TARGET_DIR"
    nx_verbose hg update "$BRANCH" || return $?
}

do_gen() # [cache] "$@"
{
    setup_vars
    nx_cd "$VMS_DIR"

    case "$CONFIG" in
        Release) local -r CONFIG_ARG="-DCMAKE_BUILD_TYPE=$CONFIG";;
        Debug) local -r CONFIG_ARG="";;
    esac

    local -i CACHE_ARG=0
    [ "$1" = "cache" ] && { shift; CACHE_ARG=1; }

    if [ -d "$CMAKE_BUILD_DIR" ]
    then
        nx_echo "WARNING: Dir $CMAKE_BUILD_DIR already exists."
        if [ $CACHE_ARG = 0 ]
        then
            local -r CMAKE_CACHE="$CMAKE_BUILD_DIR/CMakeCache.txt"
            if [ -f "$CMAKE_CACHE" ]
            then
                nx_verbose rm "$CMAKE_CACHE"
            fi
        fi
    fi
    mkdir -p "$CMAKE_BUILD_DIR"

    nx_pushd "$CMAKE_BUILD_DIR"
    nx_echo "+ cd \"$CMAKE_BUILD_DIR\"" #< Log "cd build-dir".
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

    nx_verbose cmake "$(nx_path "$VMS_DIR")" \
        -DCMAKE_C_COMPILER_WORKS=1 -DCMAKE_CXX_COMPILER_WORKS=1 \
        $CUSTOMIZATION_ARG ${GENERATOR_ARG:+"$GENERATOR_ARG"} $TARGET_ARG $CONFIG_ARG "$@"
    local RESULT=$?

    nx_popd
    return $RESULT
}

do_build()
{
    setup_vars

    if [ ! -d "$CMAKE_BUILD_DIR" ]
    then
        nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."
    fi

    if [ "$TARGET" == "windows" ]
    then
        case "$CONFIG" in
            Release) local -r CONFIG_ARG="--config $CONFIG";;
            Debug) local -r CONFIG_ARG="";;
        esac
    else
        local -r CONFIG_ARG=""
    fi

    nx_cd "$VMS_DIR"
    time nx_verbose cmake --build "$(nx_path "$CMAKE_BUILD_DIR")" $CONFIG_ARG "$@"
}

do_run_ut() # [all|TestName] "$@"
{
    setup_vars
    nx_verbose cd "$CMAKE_BUILD_DIR"

    local TEST_NAME="$1" && shift

    local TEST_ARG
    case "$TEST_NAME" in
        all) TEST_ARG="";;
        "") nx_fail "Expected either 'all' or a test name as the first arg.";;
        *) TEST_ARG="-R $TEST_NAME";;
    esac

    if [ "$TARGET" == "windows" ]
    then
        local -r CONFIG_ARG="-C $CONFIG"
    else
        local -r CONFIG_ARG=""
    fi

    nx_verbose ctest $CONFIG_ARG $TEST_ARG "$@"
}

do_apidoc() # [dev|prod] "$@"
{
    setup_vars

    local TOOL="$1" && shift

    TARGET_DIR_DESCRIPTION="$CMAKE_BUILD_DIR"
    API_XML=$(nx_path "$CMAKE_BUILD_DIR/mediaserver_core/api.xml")

    local API_TEMPLATE_XML="$VMS_DIR/mediaserver_core/api/api_template.xml"

    [ ! -f "$API_TEMPLATE_XML" ] && nx_fail "Cannot open file $API_TEMPLATE_XML"

    local JAR_DEV="$DEVELOP_DIR/devtools/apidoctool/out/apidoctool.jar"
    local JAR_PROD="$PACKAGES_DIR/any/apidoctool/apidoctool.jar"
    if [[ $TOOL = "dev" || ($TOOL = "" && -f "$JAR_DEV") ]]
    then
        local -r JAR=$(nx_path "$JAR_DEV")
        nx_echo "Executing apidoctool from devtools/ in $TARGET_DIR_DESCRIPTION"
    elif [[ $TOOL = "prod" || $TOOL = "" ]]
    then
        local -r JAR=$(nx_path "$JAR_PROD")
        nx_echo "Executing apidoctool from packages/any/ in $TARGET_DIR_DESCRIPTION"
    else
        nx_fail "Invalid apidoctool location \"$TOOL\": expected \"dev\" or \"prod\"."
    fi

    if [ -z "$1" ]
    then #< No other args - run apidoctool to generate documentation.
        nx_verbose java -jar "$JAR" -verbose code-to-xml -vms-path "$(nx_path "$VMS_DIR")" \
            -template-xml "$(nx_path "$API_TEMPLATE_XML")" -output-xml "$API_XML"
        RESULT=$?
    else #< Some args specified - run apidoctool with the specified args.
        nx_verbose java -jar "$JAR" "$@"
        RESULT=$?
    fi
    nx_echo
    nx_verbose cmake -E copy_if_different \
        "$API_XML" $(nx_path "$CMAKE_BUILD_DIR/mediaserver_core/resources/static/") \
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

    nx_verbose java -jar "$(nx_path "$JAR_DEV")" \
        -verbose test -test-path "$(nx_path "$TEST_DIR")" \
        || exit $?

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

    # "Makefiles" and "gcc" are needed for cygwin support.
    nx_verbose cmake "$SRC" -G 'Unix Makefiles' -DCMAKE_C_COMPILER=gcc || return $?

    nx_verbose cmake --build . "$@" || return $?
    ./nx_kit_*
}

do_kit() # "$@"
{
    setup_vars

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
    build_and_test_nx_kit "$KIT_SRC_DIR" || { local RESULT=$?; nx_popd; return $?; }

    nx_popd
    if [[ $KEEP_BUILD_DIR == 0 ]]
    then
        rm -rf "$KIT_BUILD_DIR"
    else
        nx_echo
        nx_echo "ATTENTION: Built at $KIT_BUILD_DIR"
        nx_echo
    fi

    nx_verbose rm -r "$PACKAGES_DIR/any/nx_kit/src"
    nx_verbose cp -r "$KIT_SRC_DIR/src" "$PACKAGES_DIR/any/nx_kit/" || return $?
    nx_verbose cp -r "$KIT_SRC_DIR/nx_kit.cmake" "$PACKAGES_DIR/any/nx_kit/" || return $?
    nx_echo
    nx_echo "SUCCESS: $NX_KIT_DIR/src and nx_kit.cmake copied to packages/any/"
}

log_build_vars()
{
    echo "+ TARGET=$TARGET CONFIG=$CONFIG"
}

do_cmake() # "$@"
{
    do_gen "$@" || return $?

    if ! nx_is_cygwin
    then
        ( cd "$CMAKE_BUILD_DIR"
            nx_verbose "$NINJA_CLEAN_TOOL"
        ) || return $?
    fi

    do_build
}

build_distrib() # "$@"
{
    do_cmake "$@" -DwithDistributions=ON
}

list_tar_gz() # CHECKSUM archive.tar.gz listing.txt
{
    local -r -i CHECKSUM="$1"; shift
    local -r ARCHIVE="$1"; shift
    local -r LISTING="$1"; shift

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

test_distrib_tar_gz() # CHECKSUM original.tar.gz built.tar.gz
{
    local -r -i CHECKSUM="$1"; shift
    local -r ORIGINAL_TAR_GZ="$1"; shift
    local -r BUILT_TAR_GZ="$1"; shift

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

    nx_verbose diff "$ORIGINAL_LISTING" "$BUILT_LISTING" \
        || nx_fail "Archives are different; see above."

    rm "$ORIGINAL_LISTING"
    rm "$BUILT_LISTING"
    nx_echo "SUCCESS: The built .tar.gz contains the same files as the original one."
}

test_distrib_zip() # original.zip built.zip built.tar.gz
{
    local -r ORIGINAL_ZIP="$1"; shift
    local -r BUILT_ZIP="$1"; shift
    local -r BUILT_TAR_GZ="$1"; shift

    nx_echo "Comparing .zip archives (.tar.gz compared to the one built):"

    # Unpack original.zip - do this every time to allow the .zip file to be updated by the user.
    local ORIGINAL_ZIP_UNPACKED="${ORIGINAL_ZIP%.zip}"
    rm -rf "$ORIGINAL_ZIP_UNPACKED"
    mkdir -p "$ORIGINAL_ZIP_UNPACKED"
    unzip -q "$ORIGINAL_ZIP" -d "$ORIGINAL_ZIP_UNPACKED" || nx_fail "Unzipping failed, see above."

    local BUILT_ZIP_UNPACKED="${ORIGINAL_ZIP%.zip}.BUILT"
    rm -rf "$BUILT_ZIP_UNPACKED"
    mkdir -p "BUILT_ZIP_UNPACKED"
    unzip -q "$BUILT_ZIP" -d "$BUILT_ZIP_UNPACKED" || nx_fail "Unzipping failed, see above."

    # Tar.gz in zips can be bitwise-different, thus, compare tar.gz in built zip to built tar.gz.
    nx_verbose diff "$BUILT_TAR_GZ" "$BUILT_ZIP_UNPACKED/$(basename "$BUILT_TAR_GZ")" \
        || nx_fail "The .tar.gz archive in .zip differs from the one built."

    nx_verbose diff -r "$ORIGINAL_ZIP_UNPACKED" "$BUILT_ZIP_UNPACKED" \
        --exclude $(basename "$BUILT_TAR_GZ") \
        || nx_fail "The .zip archives are different; see above."

    rm -r "$ORIGINAL_ZIP_UNPACKED"
    rm -r "$BUILT_ZIP_UNPACKED"
    nx_echo "SUCCESS: The built .zip contains the proper .tar.gz, and other files equal originals."
}

do_test_distrib() # [checksum] [no-build] orig/archives/dir
{
    setup_vars
    nx_cd "$VMS_DIR"

    local -r TAR_GZ_MASK="nxwitness-*.tar.gz"
    local -r ZIP_MASK="nxwitness-*_update*.zip"
    local -r DEBUG_TAR_GZ_SUFFIX="-debug-symbols.tar.gz"

    local -i CHECKSUM=0; [ "$1" = "checksum" ] && { shift; CHECKSUM=1; }
    local -i NO_BUILD=0; [ "$1" = "no-build" ] && { shift; NO_BUILD=1; }

    if [ ! -d "$CMAKE_BUILD_DIR" ]
    then
        nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."
    fi

    if [ $NO_BUILD = 0 ]
    then
        build_distrib || return $?
    fi

    local BUILT_TAR_GZ
    nx_find_file BUILT_TAR_GZ "main .tar.gz installer" "$CMAKE_BUILD_DIR" -name "$TAR_GZ_MASK" \
        ! -name "*$DEBUG_TAR_GZ_SUFFIX"

    local BUILT_ZIP
    nx_find_file BUILT_ZIP "installer .zip" "$CMAKE_BUILD_DIR" -name "$ZIP_MASK"

    local -r ORIGINAL_DIR="$1"
    local -r ORIGINAL_TAR_GZ="$ORIGINAL_DIR"/$(basename "$BUILT_TAR_GZ")

    # Test main distrib .tar.gz.
    nx_echo
    test_distrib_tar_gz $CHECKSUM "$ORIGINAL_TAR_GZ" "$BUILT_TAR_GZ"

    # Also test the archive with debug libraries, if its sample is present in the "original" dir.
    local -r ORIGINAL_DEBUG_TAR_GZ="$ORIGINAL_TAR_GZ$DEBUG_TAR_GZ_SUFFIX"
    local -r BUILT_DEBUG_TAR_GZ="$BUILT_TAR_GZ$DEBUG_TAR_GZ_SUFFIX"
    if [ -f "$ORIGINAL_DEBUG_TAR_GZ" ]
    then
        nx_echo
        test_distrob_tar_gz $CHECKSUM "$ORIGINAL_DEBUG_TAR_GZ" "$BUILT_DEBUG_TAR_GZ"
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
    test_distrib_zip "$ORIGINAL_ZIP" "$BUILT_ZIP" "$BUILT_TAR_GZ"
    nx_echo
    nx_echo "All tests SUCCEEDED."
}

printRepos()
{
    # Allow current dir to be either DEVELOP_DIR or any of its subdirs.
    if [ "$(readlink -f $(pwd))" != "$(readlink -f "$DEVELOP_DIR")" ]
    then
        setup_vars
        cd "$VMS_DIR/.."
    fi

    local -A EXTRAS #< map<repo, extra_info_if_any>
    local -A BRANCHES #< map<repo, branch>

    local REPO
    for REPO in $(find * -maxdepth 2 -path "*/.hg/branch" -type f -printf '%H\n')
    do
        # Check if the repo dir is mounted from a Windows filesystem.
        local WIN_DIR=$(mount |grep "$HOME/develop/$REPO " |awk '{print $1}')
        if [ ! -z "$WIN_DIR" ]
        then
            local EXTRA
            local WIN_REPO=$(basename "$WIN_DIR")
            if [ "$WIN_REPO" != "$REPO" ]
            then
                EXTRA=" $WIN_REPO"
            fi
            EXTRAS+=( ["$REPO"]="win$EXTRA" ) #< Add key-value.
        fi

        BRANCHES["$REPO"]="$(cat "$REPO/.hg/branch")" #< Add key-value.
    done

    # Set REPOS to sorted list of repos formed of BRANCHES keys.
    IFS=$'\n' eval 'REPOS=($(sort <<<"${!BRANCHES[*]}"))'

    # Fill BUILD_DIRS and OTHER_DIRS - non-cmake-build-dirs which names start with any repo name.
    local -A BUILD_DIRS #< map<repo, cmake_build_dir>
    local OTHER_DIRS=()
    local DIR
    for DIR in *
    do
        if [ ! -d "$DIR" ]
        then
            continue
        fi

        local -i IS_PREFIX=0
        local -i IS_EQUAL=0
        for REPO in "${REPOS[@]}"
        do
            if [[ $DIR =~ ^$REPO.+ ]]
            then
                IS_PREFIX=1
            fi
            if [ "$DIR" = "$REPO" ]
            then
                IS_EQUAL=1
            fi
        done

        if [ $IS_PREFIX == 1 ] && [ $IS_EQUAL == 0 ]
        then
            # Check CMakeCache.txt to have: CMAKE_HOME_DIRECTORY:INTERNAL=<CMAKE_SRC_DIR>
            local CMAKE_SRC_DIR=$(cat "$DIR/CMakeCache.txt" 2>/dev/null \
                |grep 'CMAKE_HOME_DIRECTORY:INTERNAL' |awk 'BEGIN { FS="=" }; { print $2 }')
            if [ -z "$CMAKE_SRC_DIR" ]
            then
                OTHER_DIRS+=( "$DIR" )
            else
                BUILD_DIRS["$(basename "$CMAKE_SRC_DIR")"]+="$DIR "
            fi
        fi
    done

    # Print repo dirs.
    for REPO in "${REPOS[@]}"
    do
        local BUILD_DIR_STR=""
        if [ ! -z "${BUILD_DIRS[$REPO]}" ]
        then
            local DIRS=( ${BUILD_DIRS[$REPO]} ) #< Split by spaces into array.
            if [ ${#DIRS[@]} = 1 ]
            then
                BUILD_DIR_STR=" $(nx_dcyan)=> $(nx_lcyan)${BUILD_DIRS[$REPO]}"
            else
                BUILD_DIR_STR=" $(nx_dcyan)=>$(nx_lcyan)"$'\n'
                for DIR in "${DIRS[@]}"
                do
                    BUILD_DIR_STR+="    $DIR"$'\n'
                done
            fi
        fi

        local EXTRA_STR=""
        if [ ! -z "${EXTRAS[$REPO]}" ]
        then
            EXTRA_STR="$(nx_lgray)[${EXTRAS[$REPO]}] "
        fi

        nx_echo "$EXTRA_STR$(nx_white)$REPO$BUILD_DIR_STR$(nx_dcyan):" \
            "$(nx_lyellow)${BRANCHES[$REPO]}$(nx_nocolor)"
    done

    # Print other dirs.
    for DIR in "${OTHER_DIRS[@]}"
    do
        nx_echo "$(nx_lgreen)$DIR$(nx_nocolor)"
    done
}

#--------------------------------------------------------------------------------------------------

main()
{
    local COMMAND="$1"
    shift
    case "$COMMAND" in
        ini)
            touch "$TEMP_DIR"/nx_network.ini
            touch "$TEMP_DIR"/nx_network_debug.ini
            touch "$TEMP_DIR"/mobile_client.ini
            touch "$TEMP_DIR"/appserver2.ini
            touch "$TEMP_DIR"/nx_media.ini
            touch "$TEMP_DIR"/nx_streaming.ini
            touch "$TEMP_DIR"/plugins.ini
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
            # TODO: Implement for linux.
            case "$TARGET" in
                windows)
                    setup_vars
                    nx_verbose cd "$CMAKE_BUILD_DIR"

                    PATH="$QT_DIR/bin:$PATH"
                    nx_verbose bin/mediaserver -e
                    ;;
                *) nx_fail "Command not implemented yet.";;
            esac
            ;;
        stop-s)
            # TODO: Decide on better impl.
            sudo killall -9 mediaserver
            ;;
        start-c)
            # TODO: IMPLEMENT
            nx_fail "Command not implemented yet."
            ;;
        stop-c)
            # TODO: Decide on better impl.
            sudo killall -9 desktop_client
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

            local VIDEO_FILE="$1"; shift

            setup_vars

            local -r TEST_CAMERA_BIN="$CMAKE_BUILD_DIR/bin/testcamera"

            if nx_is_cygwin
            then
                PATH="$QT_DIR\bin:$CMAKE_BUILD_DIR/bin:$PATH"
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
        share)
            do_share "$@"
            ;;
        #..........................................................................................
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
            setup_vars
            if [ ! -d "$CMAKE_BUILD_DIR" ]
            then
                nx_fail "Dir $CMAKE_BUILD_DIR does not exist, run cmake generation first."
            fi
            echo "$VMS_DIR"
            echo "$CMAKE_BUILD_DIR"
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
