#!/bin/bash -xe

# currently mapped by jenkins agent script:
JUNK_SHOP_HOST=localhost
TEST_CONFIG_PATH=devtools/ci/jenkins/scalability_test/test-config.yaml


# https://stackoverflow.com/questions/1527049/join-elements-of-an-array
function join_by {
	local d=$1
	shift
	echo -n "$1"
	shift
	printf "%s" "${@/#/$d}"
}


workspace_dir="$(pwd)"

test_params=(
    merge_timeout=1h
    cameras_per_serve=20
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
    "--work-dir=$workspace_dir/work/test"
    "--bin-dir=$workspace_dir/bin"
    "--reinstall"
    "--customization=$customization"
    "--capture-db=$junk_shop_db_credentials@$JUNK_SHOP_HOST"
    "--build-parameters=$(join_by ',' ${build_parameters[@]})"
    "--run-parameters=$(join_by ',' ${test_params[@]})"
    "--test-parameters=scalability_test.$(join_by ',scalability_test.' ${test_params[@]})"
    "--tests-config-file=$workspace_dir/$TEST_CONFIG_PATH"
    )

. work/venv/bin/activate

export PYTHONPATH=$workspace_dir/devtools/ci/junk_shop
export PYTEST_PLUGINS=junk_shop.pytest_plugin

cd nx_vms/func_tests

pytest $(join_by ' ' ${options[@]}) scalability_test.py
