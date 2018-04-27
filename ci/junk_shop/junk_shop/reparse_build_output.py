#!/usr/bin/env python

# read build output artifacts from junk-shop db, try to parse
# save errors and warnings for those which do not have them.

import sys
import argparse
import time
from datetime import timedelta

from pony.orm import db_session, select, commit, desc
import faulthandler

from junk_shop.utils import DbConfig
from junk_shop import models
from junk_shop.capture_repository import DbCaptureRepository
from junk_shop.artifact import decode_artifact_data
from junk_shop.build_output_parser import parse_output_lines


PARSE_TIMEOUT = timedelta(minutes=10)


def pick_severity_lines(severity, output):
    for match in parse_output_lines(output.splitlines()):
        if match.severity == severity:
            yield match.line

def get_severity_output(severity, output):
    return '\n'.join(pick_severity_lines(severity, output))

def debug_errors(prefix, data):
    if data:
        print prefix, ('\n%s ' % prefix).join(data.splitlines())

@db_session
def reparse_build_output(repository, limit, max_id, save):
    print 'used: --max-id=%d' % max_id
    processed_count = 0
    for artifact in select(
            artifact for artifact in models.Artifact
            if artifact.full_name == 'build-output'
            and artifact.id <= max_id).order_by(desc(models.Artifact.id)):
        if artifact.run.outcome == 'passed':
            continue
        #print artifact.id, artifact.run.id, artifact.full_name, len(artifact.data), '|'.join(output[:100].splitlines())
        print artifact.id, artifact.run.id,; sys.stdout.flush()
        output = decode_artifact_data(artifact)
        print len(output), ': ',; sys.stdout.flush()
        
        faulthandler.dump_traceback_later(int(PARSE_TIMEOUT.total_seconds()), exit=True)
        t = time.time()
        errors = get_severity_output('error', output)
        parse_time = time.time() - t
        faulthandler.cancel_dump_traceback_later()
        
        #debug_errors('*', errors)
        error_artifact_list = artifact.run.artifacts.filter(lambda a: a.full_name== 'build-errors')
        if error_artifact_list.exists():
            old_errors = decode_artifact_data(error_artifact_list.get())
            #debug_errors('+', old_errors)
            if old_errors == errors:
                print parse_time, '%d errors match' % len(errors.splitlines())
            else:
                print parse_time, '* errors does NOT match; was %d, parsed %d *' % (
                    len(old_errors.splitlines()), len(errors.splitlines()))
            continue
        if errors:
            if save:
                repository.add_artifact(artifact.run, 'build-errors', 'build-errors', repository.artifact_type.output, errors, is_error=True)
                print parse_time, 'saving %d errors' % len(errors.splitlines()),
                commit()
            else:
                print parse_time, 'parsed %d errors' % len(errors.splitlines()),
        else:
            print parse_time, 'parsed no errors',
        run = artifact.run
        build = run.build
        if run.customization:
            customization = run.customization
        else:
            customization = build.customization
        if customization:
            customization_name = customization.name
        else:
            customization_name = 'none'
        print '  : http://junkshop.enk.me/project/{}/{}/{}/{}/{}'.format(
            build.project.name, build.branch.name, build.build_num, customization_name, run.platform.name)
        processed_count += 1
        if processed_count >= limit:
            break
    print 'use next: --max-id=%d' % (artifact.id - 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--limit', type=int, help='Limit processed record count')
    parser.add_argument('--max-id', type=int, default=999999999, help='Maximum artifact id to check')
    parser.add_argument('--save', action='store_true', help='Save parsed errors to db')
    args = parser.parse_args()
    repository = DbCaptureRepository(args.db_config, build_parameters=None)
    reparse_build_output(repository, limit=args.limit, max_id=args.max_id, save=args.save)


if __name__ == '__main__':
    main()
