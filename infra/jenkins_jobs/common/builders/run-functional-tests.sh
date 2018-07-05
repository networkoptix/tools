set -xe

# must be injected by job template or macros
: ${JUNK_SHOP_CAPTURE_DB:?}
: ${AUTOTEST_EMAIL_PASSWORD:?}
: ${PROJECT:?}
: ${BRANCH:?}
: ${BUILD_NUM:?}
: ${CUSTOMIZATION:?}
: ${PLATFORM:?}
: ${CLOUD_GROUP:?}
: ${WORK_DIR:?}
: ${BIN_DIR:?}
: ${MEDIASERVER_DIST_DIR:?}
: ${CLEAN:?}  # 'true'/'True' or 'false'/'False'
: ${TEST_SELECT_EXPR?}
: ${TEST_LIST?}  # space-delimited; empty means run all tests
: ${TIMEOUT_SEC:?}
: ${SLOT:?}  # aka executor number, 0..

[ -d "$BIN_DIR" ]  # expected to exist
mkdir -p "$WORK_DIR"

VM_PORT_BASE=20000  # base for REST API ports forwarded from vm to host
VM_PORT_RANGE=100  # how many forwarded ports one functional tests run may require, max

VM_PORT=$(($VM_PORT_BASE + $SLOT * $VM_PORT_RANGE))
VM_NAME_PREFIX="funtest-$SLOT-"

MEDIASERVER_DIST_PATH="$(echo $MEDIASERVER_DIST_DIR/*-server-*.deb)"

BUILD_PARAMETERS=(
    "project=$PROJECT"
    "branch=$BRANCH"
    "build_num=$BUILD_NUM"
    "platform=$PLATFORM"
    "customization=$CUSTOMIZATION"
    )

OPTIONS=(
    "--work-dir=$WORK_DIR"
    "--bin-dir=$BIN_DIR"
    "--mediaserver-installers-dir=$MEDIASERVER_DIST_DIR"
    "--mediaserver-dist-path=$MEDIASERVER_DIST_PATH"
    "--customization=$CUSTOMIZATION"
    "--cloud-group=$CLOUD_GROUP"
    "--timeout=$TIMEOUT_SEC"
    "--capture-db=$JUNK_SHOP_CAPTURE_DB"
    "--build-parameters=$(join_by ',' ${BUILD_PARAMETERS[@]})"
    "--vm-port-base=$VM_PORT"
    "--vm-name-prefix=$VM_NAME_PREFIX"
)

if [[ "$CLEAN" == "true" || "$CLEAN" == "True" ]]; then
	OPTIONS=(
		"${OPTIONS[@]}"
		"--reinstall"
	)
fi


if [[ "$VERBOSE" == "true" ]] ; then
  OPTIONS=(
    "${OPTIONS[@]}"
    "-s"
  )
fi

source venv/bin/activate

export PYTHONPATH=$WORKSPACE/devtools/ci/junk_shop
export PYTEST_PLUGINS=junk_shop.pytest_plugin
# JUNK_SHOP_CAPTURE_DB is used by tests

cd nx_vms/func_tests

if [[ "$TEST_SELECT_EXPR" != "" ]]; then
	pytest $(join_by ' ' ${OPTIONS[@]}) -k "$TEST_SELECT_EXPR" $TEST_LIST
else
	pytest $(join_by ' ' ${OPTIONS[@]}) $TEST_LIST
fi
