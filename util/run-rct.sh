#!/bin/bash
set -e -x

ARGS=${@:-"--collect-only"}
mkdir -p ${RUN_DIR:="$PWD-run"}

[ ! -d "$RUN_DIR"/venv ] && python3 -m venv "$RUN_DIR"/venv
source "$RUN_DIR"/venv/bin/activate

if which tox; then
    tox -e $(python3 -c 'import sys; print("py3" + str(sys.version_info.minor))')
fi

python3 -m pip install -r requirements.txt
if ! pytest -s $ARGS; then
    if [ "$ARGS" == "real_camera_tests/test_server.py" ]; then
        REPORT=$(find "$RUN_DIR"/work/latest/ -name test_results.json)
        [ -f "$REPORT" ] && firefox "$REPORT" >/dev/null 2>&1 &
    fi
fi
