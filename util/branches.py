#!/usr/bin/env python

import argparse
from datetime import timedelta
from itertools import groupby
from common_module import *
from hg_module import get_branches

tooOld = timedelta(days=30)
verbose = False

# Branches which are never to be closed
exclusions = [
    'meta',
    'vms_gui',
    'vms_server',
    'default',
    'mobile',
    'mobile_release'
]


def group_branches():
    branches = [branch for branch in get_branches() if branch.name not in exclusions]

    def userKey(branch):
        return branch.user

    branches.sort(key=userKey)
    return groupby(branches, userKey)


def print_branches(grouped_branches):
    prevUser = ''

    for user, branches_iter in grouped_branches:
        branches = [i for i in branches_iter if verbose or not i.active or i.age > tooOld]
        if len(branches) == 0:
            continue

        if prevUser != '':
            separator()
        prevUser = user
        info(user)
        for branch in sorted(branches, key=lambda x: not x.active):
            branch_name = str(branch.name).ljust(40)
            if not branch.active:
                err(branch_name + '(INACTIVE)')
            elif branch.age > tooOld:
                warn(branch_name + '(TOO OLD: ' + str(branch.age.days) + ' days)')
            elif verbose:
                info(branch_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    branches = group_branches()
    print_branches(branches)


if __name__ == "__main__":
    main()
