#!/usr/bin/env python

# pick changeset log for a run from mercurial, save to junk-shop database

import argparse
import subprocess
from junk_shop.utils import DbConfig, datetime_utc_now, status2outcome
from junk_shop import models
from junk_shop.capture_repository import project_type, BuildParameters, DbCaptureRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('db_config', type=DbConfig.from_string, metavar='user:password@host',
                        help='Capture postgres database credentials')
    parser.add_argument('--project', type=project_type, help='Junk-shop project name')
    parser.add_argument('--build-parameters', type=BuildParameters.from_string, metavar=BuildParameters.example,
                        help='Build parameters; project, branch and changeset are the (only) required ones')
    args = parser.parse_args()
    repository = DbCaptureRepository(args.db_config, args.project, args.build_parameters)


if __name__ == '__main__':
    main()
