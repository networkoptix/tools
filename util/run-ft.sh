#!/bin/bash
if [[ "$1" == --help ]] || [[ "$1" == -h ]]; then cat <<END
Installs FT dependencies, runs tox and FT, opens RCT report.
Usage: $0 [pytest args...]
END
exit 0; fi

set -e -x

RUN="python3.7 -m"
ARGS=${@:-"--collect-only"}
mkdir -p ${RUN_DIR:="$PWD-run"}

[ ! -d "$RUN_DIR"/venv ] && $RUN venv "$RUN_DIR"/venv
source "$RUN_DIR"/venv/bin/activate

$RUN pip install tox && $RUN tox
$RUN pip install -r requirements.txt || true #< Workaround unpredictable crash.
$RUN pytest $ARGS || true #< Processing results anyway.

# Analyse RCT results if any.
REPORT=$(find "$RUN_DIR"/work/latest/ -name test_results.json)
[ -f "$REPORT" ] && firefox "$REPORT" >/dev/null 2>&1 &

