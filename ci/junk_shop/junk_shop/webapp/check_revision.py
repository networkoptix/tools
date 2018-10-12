"""
    check_revision.py
    ~~~~~~~~~~~~~~~~~
    An API endpoint to get information about nx_vms revision to make a 'merge' decision.
    http://junkshop.enk.me/check_revision/<REVISION>, where revision is a hexadecimal
    string less than 40 characters long, referred to as a short-form identifier.

    URL sample: http://junkshop.enk.me/check_revision/2086ef2753e7

    The response contains platforms dictionary with stage statuses in JSON format.

    Response sample:

    ```json
    {
        "bpi":
        {
            "build": "passed"
        },
        "linux-x64":
        {
            "build": "passed",
            "functional": "failed",
            "unit": "passed"
        },
        "mac":
        {
            "build": "failed",
        },
        "webadmin":
        {
            "build": "passed"
        },
        "windows-x64":
        {
            "build": "passed",
            "unit": "failed"
        }
    }
    ```
"""

from pony.orm import db_session, select
from junk_shop.webapp import app
from .. import models
from .utils import STAGE_NAMES
from flask import jsonify, request

DEFAULT_PROJECT = 'ci'
OUTCOME_PASSED = 'passed'


@app.route('/check_revision/<revision>', methods=['GET'])
@db_session
def check_revision(revision):
    result = dict()
    project = request.args.get('project', DEFAULT_PROJECT)
    query = select(run for run in models.Run
                   if run.build.revision == revision
                   and run.test.path in STAGE_NAMES
                   and run.build.project.name == project)
    for run in query:
        platform_dict = result.setdefault(run.platform.name, dict())
        if (platform_dict.get(run.test.path, OUTCOME_PASSED) == OUTCOME_PASSED or
                run.outcome != OUTCOME_PASSED):
            platform_dict[run.test.path] = run.outcome
    return jsonify(result)
