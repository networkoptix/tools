set -xe

: ${JUNK_SHOP_HOST:?}  # must be injected by job template

TEST_CONFIG_PATH=devtools/ci/jenkins/scalability_test/test-config.yaml
WORKSPACE_DIR="$(pwd)"

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
    "branch=$branch"
    "build_num=$build_num"
    "platform=$platform"
    "customization=$customization"
    )
options=(
    "--work-dir=$WORKSPACE_DIR/work/test"
    "--bin-dir=$WORKSPACE_DIR/bin"
    "--reinstall"
    "--customization=$customization"
    "--capture-db=$junk_shop_db_credentials@$JUNK_SHOP_HOST"
    "--build-parameters=$(join_by ',' ${build_parameters[@]})"
    "--run-parameters=$(join_by ',' ${test_params[@]})"
    "--run-name=scalability"
    "--test-parameters=scalability_test.$(join_by ',scalability_test.' ${test_params[@]})"
    "--tests-config-file=$WORKSPACE_DIR/$TEST_CONFIG_PATH"
    )

source work/venv/bin/activate

export PYTHONPATH=$WORKSPACE_DIR/devtools/ci/junk_shop
export PYTEST_PLUGINS=junk_shop.pytest_plugin

cd nx_vms/func_tests

pytest $(join_by ' ' ${options[@]}) scalability_test.py
