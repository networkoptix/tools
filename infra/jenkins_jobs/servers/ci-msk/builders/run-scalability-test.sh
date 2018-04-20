set -xe

# must be injected by job template
: ${WORKSPACE:?}
: ${JUNK_SHOP_CAPTURE_DB:?}
: ${BRANCH:?}
: ${BUILD_NUM:?}
: ${CUSTOMIZATION:?}
: ${PLATFORM:?}
: ${USE_LIGHTWEIGHT_SERVERS:?}
: ${SERVER_COUNT:?}

TEST_CONFIG_PATH=$WORKSPACE/devtools/ci/jenkins/scalability_test/test-config.yaml

test_params=(
    merge_timeout=1h
    cameras_per_server=20
    users_per_server=4
    properties_per_camera=5
	use_lightweight_servers=$USE_LIGHTWEIGHT_SERVERS
	server_count=$SERVER_COUNT
    )
build_parameters=(
    "project=ci"
    "branch=$BRANCH"
    "build_num=$BUILD_NUM"
    "platform=$PLATFORM"
    "customization=$CUSTOMIZATION"
    )
options=(
    "--work-dir=$WORKSPACE/work/test"
    "--bin-dir=$WORKSPACE/bin"
    "--reinstall"
    "--customization=$CUSTOMIZATION"
    "--capture-db=$JUNK_SHOP_CAPTURE_DB"
    "--build-parameters=$(join_by ',' ${build_parameters[@]})"
    "--run-parameters=$(join_by ',' ${test_params[@]})"
    "--run-name=scalability"
    "--test-parameters=scalability_test.$(join_by ',scalability_test.' ${test_params[@]})"
    "--tests-config-file=$TEST_CONFIG_PATH"
    )

source venv/bin/activate

export PYTHONPATH=$WORKSPACE/devtools/ci/junk_shop
export PYTEST_PLUGINS=junk_shop.pytest_plugin

cd nx_vms/func_tests

pytest $(join_by ' ' ${options[@]}) scalability_test.py
