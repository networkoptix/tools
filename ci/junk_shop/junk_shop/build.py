#!/usr/bin/env python

# read build output from stdin, exit code as an argument, store all to database

import sys
import os.path
import argparse
from collections import namedtuple
import re

from pathlib2 import Path
from pony.orm import db_session

from junk_shop.utils import datetime_utc_now, status2outcome, outcome2status
from junk_shop import models
from junk_shop.parameters import add_db_arguments, create_db_repository
from junk_shop.build_output_parser import parse_output_lines


def parse_maven_output(output):
    for line in output.splitlines():
        mo = re.match(r'^\[INFO\] BUILD (SUCCESS|FAILURE)$', line.rstrip())
        if mo:
            return mo.group(1) == 'SUCCESS'
    return False

def load_output_file_list(output_file_list):
    output = ''
    for file_path in output_file_list:
        if os.path.isfile(file_path):
            with open(file_path) as f:
                output += f.read()
        else:
            print >>sys.stderr, 'Build output file is missing: %s' % file_path
    return output


def pick_severity_lines(severity, output):
    for match in parse_output_lines(output.splitlines()):
        if match.severity == severity:
            yield match.line

def get_severity_output(severity, output):
    return '\n'.join(pick_severity_lines(severity, output))


StoredBuildInfo = namedtuple('StoredBuildInfo', 'passed outcome run_id')

@db_session
def store_output_and_error(repository, output, succeeded, error_message, parse_maven_outcome=False):
    passed = succeeded
    test = repository.produce_test('build', is_leaf=True)
    run = repository.add_run('build', test=test)
    repository.add_artifact(run, 'output', 'build-output', repository.artifact_type.output, output)
    errors = get_severity_output('error', output)
    warnings = get_severity_output('warning', output)
    if errors:
        repository.add_artifact(run, 'build-errors', 'build-errors', repository.artifact_type.output, errors, is_error=True)
    if warnings:
        repository.add_artifact(run, 'build-warnings', 'build-warnings', repository.artifact_type.output, warnings)
    if parse_maven_outcome:
        outcome = parse_maven_output(output)
        if not outcome:
            passed = False
    if error_message:
        repository.add_artifact(
            run, 'error', 'build-error', repository.artifact_type.output, error_message, is_error=True)
    outcome = status2outcome(passed)
    run.outcome = outcome
    return StoredBuildInfo(passed, outcome, run.id)


def str2status(value):
    if not value:
        return True
    return outcome2status(value)

def main():
    parser = argparse.ArgumentParser()
    add_db_arguments(parser)
    parser.add_argument('--outcome', type=str2status, default='passed',
                            help='Build outcome, "passed" of "failed"; default is passed')
    parser.add_argument('--error-message', help='Build error to store to db')
    parser.add_argument('--parse-maven-outcome', action='store_true', dest='parse_maven_outcome',
                        help='Parse output to determine maven outcome')
    parser.add_argument('--signal-failure', action='store_true', help='Exit with code 2 if this build is failed one')
    parser.add_argument('output_file', type=Path, help='Build output file')
    args = parser.parse_args()
    try:
        output = args.output_file.read_text()
        repository = create_db_repository(args)
        build_info = store_output_and_error(
            repository,
            output,
            args.outcome,
            args.error_message,
            args.parse_maven_outcome,
            )
        print 'Created %s run#%d' % (build_info.outcome, build_info.run_id)
        if not build_info.passed and args.signal_failure:
            sys.exit(2)
    except RuntimeError as x:
        print x
        sys.exit(1)


if __name__ == '__main__':
    main()
