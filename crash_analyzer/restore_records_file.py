#!/usr/bin/env python3

import argparse
import logging
from typing import List

import crash_info
import jira
import external_api
import utils

logger = logging.getLogger(__name__)

NAME = 'Crash Monitor Records Restorer'
VERSION = '2.0'


def extract_records_from_issues(issues: List[jira.resources.Issue]):
    records = {}
    logger.info("Processing {} JIRA issues".format(len(issues)))
    for issue in issues:
        if not issue.fields.description:
            logger.warning("Skipping JIRA issue {}. Empty description".format(issue.key))
            continue

        # Some of the issues could be edited or created manually. Ignoring them.
        _, open_tag, *stack, close_tag = issue.fields.description.splitlines()
        if not open_tag == close_tag == "{code}":
            logger.warning("Skipping JIRA issue {}. Invalid description".format(issue.key))
            continue

        if len(issue.fields.components) == 0:
            logger.warning("Skipping JIRA issue {}. No attachments".format(issue.key))
            continue

        reason_args = {}
        reason_args["component"] = str(issue.fields.components[0])
        reason_args["code"] = issue.fields.summary.split(":")[-1].strip()
        reason_args["stack"] = stack

        reason = crash_info.Reason(**reason_args)
        record_data = {"crash_id": reason.crash_id, "issue": issue.key}
        for attachment in issue.fields.attachment:
            if attachment.filename.endswith(".dmp") or attachment.filename.endswith(".gdb-bt"):
                records[attachment.filename] = record_data

    return records


def restore_records_file(records_filename: str, thread_count: int, **options):
    assert records_filename.endswith(".json")

    jira = external_api.Jira(**options)
    issues = jira.all_issues(max_results=None, fields=["attachment", "summary", "components", "description"])
    records = extract_records_from_issues(issues)
    records_file = utils.File(records_filename)
    records_file.serialize(records)


def main():
    try:
        import subprocess
        change_set, *_ = subprocess.check_output(["hg", "id"]).decode().split()
    except (ImportError, OSError):
        change_set = 'UNKNOWN'

    parser = argparse.ArgumentParser('{} version {}.{}'.format(NAME, VERSION, change_set))
    parser.add_argument('config_file', help="Same config as the one used for the Crash Monitor,"
                                            " only 'logging' and 'upload' groups are required")
    parser.add_argument('-f', '--records-file', default="records.json", help="File where all records should be written")
    parser.add_argument('-o', '--override', action='append', default=[], help='SECTION.KEY=VALUE to override config')

    arguments = parser.parse_args()
    config = utils.File(arguments.config_file).parse()
    for override in arguments.override:
        utils.update_dict(config, override)

    utils.setup_logging(**config.pop('logging'), title=(parser.prog + ', config: ' + arguments.config_file))
    restore_records_file(arguments.records_file, **config["upload"])


if __name__ == '__main__':
    main()
