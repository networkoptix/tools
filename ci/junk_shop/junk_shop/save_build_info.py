#!/usr/bin/env python

# pick changeset log for a run from mercurial, save to junk-shop database
# hg log  --template '{node|short}|{date}|{author|person}|{author|email}|{desc|firstline|utf8}\n' --rev 5886b93ee64d..ce6f050b6b3a

import argparse
import subprocess
from datetime import datetime, timedelta
import pytz
from pony.orm import db_session, select, desc
from junk_shop.utils import DbConfig
from junk_shop import models
from junk_shop.capture_repository import BuildParameters, DbCaptureRepository


HG_LOG_TEMPLATE = r'{node|short}|{date}|{author|person}|{author|email}|{desc|firstline|utf8}\n'


def pick_last_revision(repository):
    parameters = repository.build_parameters
    prev_build = select(
        build for build in models.Build
        if build.project.name == parameters.project and
           build.branch.name == parameters.branch and
           build.revision and
           build.build_num < parameters.build_num).order_by(desc(1)).first()
    return prev_build.revision

def make_datetime(timestamp, offset_sec):
    offset = timedelta(seconds=offset_sec)
    for tz in pytz.all_timezones:
        tzinfo = pytz.timezone(tz)
        dt = datetime.fromtimestamp(timestamp, tzinfo)
        if dt.utcoffset() == offset:
            return dt
    assert False, 'Unusual time zone offset: %s' % offset

def delete_build_changesets(build):
    select(cs for cs in models.BuildChangeSet if cs.build is build).delete()

def load_change_sets(repository, src_dir, build, prev_revision):
    rev_range = '%s..%s' % (prev_revision, build.revision)
    args = ['hg', 'log', '--template', HG_LOG_TEMPLATE, '--rev', rev_range]
    output = subprocess.check_output(args, cwd=src_dir)
    for line in output.splitlines():
        revision, date_str, user, email, desc = line.split('|', 4)
        timestamp, offset_sec = date_str.split('-')
        date = make_datetime(float(timestamp), int(offset_sec))
        print revision, date, user, email, desc
        changeset = models.BuildChangeSet(
            build=build,
            revision=revision,
            date=date,
            user=user,
            email=email,
            desc=desc,
            )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('src_dir', help='Source code directory to load changesets from')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters; project, branch and changeset are the (only) required ones')
    args = parser.parse_args()
    repository = DbCaptureRepository(args.db_config, args.build_parameters)
    with db_session:
        build = repository.produce_build()
        prev_revision = pick_last_revision(repository)
        print 'current revision: %s, prev_revision: %s' % (build.revision, prev_revision)
        delete_build_changesets(build)
        load_change_sets(repository, args.src_dir, build, prev_revision)


if __name__ == '__main__':
    main()
