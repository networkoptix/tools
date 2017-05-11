#!/usr/bin/env python

# read build output from stdin, exit code as an argument, store all to database

import sys
import argparse
from pony.orm import db_session
from junk_shop.utils import DbConfig, datetime_utc_now, status2outcome
from junk_shop import models
from junk_shop.capture_repository import Parameters, DbCaptureRepository


@db_session
def store_output_and_exit_code(repository, output, exit_code):
    passed = exit_code == 0
    test = repository.produce_test('build', is_leaf=True)
    run = repository.add_run('build', test=test)
    run.outcome = status2outcome(passed)
    repository.add_artifact(run, 'output', repository.artifact_type.output, output)
    if exit_code != 0:
        exit_code_message = 'Exit code: %d' % exit_code
        repository.add_artifact(
            run, 'exit code', repository.artifact_type.output, exit_code_message, is_error=not passed)
    print 'Created %s run %s' % (run.outcome, run.path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parameters', type=Parameters.from_string, metavar=Parameters.example,
                        help='Run parameters')
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('exit_code', type=int, help='Build exit code to store to db')
    args = parser.parse_args()
    try:
        repository = DbCaptureRepository(args.db_config, args.parameters)
        store_output_and_exit_code(repository, sys.stdin.read(), args.exit_code)
    except RuntimeError as x:
        print x
        sys.exit(1)


if __name__ == '__main__':
    main()
