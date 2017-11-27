#!/usr/bin/env python

# read build output from stdin, exit code as an argument, store all to database

import sys
import os.path
import argparse
import re
from pony.orm import db_session
from junk_shop.utils import DbConfig, datetime_utc_now, status2outcome
from junk_shop import models
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository


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


@db_session
def store_output_and_exit_code(db_config, build_parameters, exit_code, parse_maven_outcome, output):
    repository = DbCaptureRepository(db_config, build_parameters)
    passed = True
    test = repository.produce_test('build', is_leaf=True)
    run = repository.add_run('build', test=test)
    repository.add_artifact(run, 'output', 'build-output', repository.artifact_type.output, output)
    if parse_maven_outcome:
        outcome = parse_maven_output(output)
        if not outcome:
            passed = False
    if exit_code is not None and exit_code != 0:
        passed = False
        exit_code_message = 'Exit code: %d' % exit_code
        repository.add_artifact(
            run, 'exit code', 'build-exit-code', repository.artifact_type.output, exit_code_message, is_error=not passed)
    run.outcome = status2outcome(passed)
    print 'Created %s run %s' % (run.outcome, run.path)
    return passed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters')
    parser.add_argument('--exit-code', type=int, dest='exit_code', help='Exit code from the build to store to db')
    parser.add_argument('--parse-maven-outcome', action='store_true', dest='parse_maven_outcome',
                        help='Parse output to determine maven outcome')
    parser.add_argument('--signal-failure', action='store_true', help='Exit with code 2 if this build is failed one')
    parser.add_argument('output_file', nargs='+', help='Build output file')
    args = parser.parse_args()
    try:
        output = load_output_file_list(args.output_file)
        passed = store_output_and_exit_code(
            args.db_config,
            args.build_parameters,
            args.exit_code,
            args.parse_maven_outcome,
            output,
            )
        if not passed and args.signal_failure:
            sys.exit(2)
    except RuntimeError as x:
        print x
        sys.exit(1)


if __name__ == '__main__':
    main()
