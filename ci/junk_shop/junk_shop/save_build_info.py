#!/usr/bin/env python

# pick changeset log for a run from mercurial, save to junk-shop database

import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from collections import namedtuple

import dateutil.parser as dateutil_parser
from pony.orm import db_session, select, desc

from junk_shop import models
from junk_shop.parameters import add_db_arguments, create_db_repository


log = logging.getLogger(__name__)


HG_LOG_TEMPLATE = r'{node|short}|{date|isodatesec}|{author|person}|{author|email}|{desc|firstline}\n'


RevisionInfo = namedtuple('RevisionInfo', 'prev_revision current_revision')


def pick_last_revision(repository):
    parameters = repository.build_parameters
    prev_build = select(
        build for build in models.Build
        if build.project.name == parameters['project'] and
           build.branch.name == parameters['branch'] and
           build.build_num < parameters['build_num']).order_by(desc(1)).first()
    if prev_build:
        return prev_build.revision
    else:
        return None

def delete_build_changesets(build):
    select(cs for cs in models.BuildChangeSet if cs.build is build).delete()

def load_change_sets(repository, src_dir, build, prev_revision):
    rev_range = build.revision + '%' + prev_revision
    args = ['hg', 'log', '--template', HG_LOG_TEMPLATE, '--rev', rev_range]
    try:
        output = subprocess.check_output(args, cwd=src_dir, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as x:
        log.error('Error retrieving repository log: %s', x.output)
        return
    lines = output.splitlines()
    for line in lines:
        revision, date_str, user, email, desc = line.split('|', 4)
        date = dateutil_parser.parse(date_str)
        log.info('Changeset: %s %s %s %s %s', revision, date, user, email, desc)
        changeset = models.BuildChangeSet(
            build=build,
            revision=revision,
            date=date,
            user=user,
            email=email,
            desc=desc.decode('utf-8'),
            )

@db_session
def update_build_info(repository, src_dir):
    build = repository.produce_build()
    prev_revision = pick_last_revision(repository)
    log.info('current revision: %s, prev_revision: %s', build.revision, prev_revision)
    delete_build_changesets(build)
    if prev_revision:
        load_change_sets(repository, src_dir, build, prev_revision)
    return RevisionInfo(
        prev_revision=prev_revision,
        current_revision=build.revision,
        )


def main():
    parser = argparse.ArgumentParser()
    add_db_arguments(parser)
    parser.add_argument('src_dir', help='Source code directory to load changesets from')
    args = parser.parse_args()

    format = '%(asctime)-15s %(threadName)-15s %(levelname)-7s %(message).500s'
    logging.basicConfig(level=logging.INFO, format=format)

    repository = create_db_repository(args)
    for param in ['project', 'branch', 'build_num', 'revision']:
        assert param in repository.build_parameters, '%s build parameter is required' % param

    update_build_info(repository, args.src_dir)


if __name__ == '__main__':
    main()
