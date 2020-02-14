#!/usr/bin/env python3

"""
This script creates merge commit and it's description.

PLEASE NOTE:
This script is completely useless for git and is written only for backward
compatibility with miserable and feature-lacking mercurial. Consider using git commands instead.

TODO: '--patience' flag should be tried for difficult merges


Examples:
1. prod_2.5 to current branch merge preview
git:
    git log --oneline HEAD..prod_2.5
script:
    merge_dev.py -r prod_2.5 -p

2. Merge prod_2.5 to the current branch
git:
    git merge --no-ff --log prod_2.5
script:
    merge_dev.py -r prod_2.5

3. Merge current branch (e.g. 'dev') to prod_2.5
git:
    git checkout prod_2.5 && git merge --no-ff --log dev
script:
    merge_dev.py -t prod_2.5
"""

import subprocess
import sys
import os
import argparse
import re

verbose = False
project_keys = ['VMS', 'UT', 'CP', 'CLOUD', 'PSP', 'DESIGN', 'ENV', 'FR', 'HNW', 'LIC', 'MOBILE',
    'META', 'NCD', 'NXPROD', 'NXTOOL', 'STATS', 'CALC', 'TEST', 'VISTA', 'WEB', 'WS']


def execute_command(command, extra_args=[]):
    if verbose:
        print(">> '" + command + " ".join(extra_args) + "'")
    return subprocess.check_output(command.split() + extra_args, stderr=subprocess.STDOUT, universal_newlines=True)


def is_inside_git():
    if os.path.isdir('.git'):
        return True

    try:
        return "true" == execute_command("git rev-parse --is-inside-work-tree")
    except subprocess.CalledProcessError:
        return False
    except WindowsError:
        return False


def get_header(merged, current):
    return "Merge: {} -> {}\n".format(merged, current)


def get_current_branch():
    return execute_command("git rev-parse --abbrev-ref HEAD").strip('\n')


def has_issue_link(commit_text, project_key):
    return re.search('([^_]|\A){0}-\d+'.format(project_key.lower()), commit_text.lower()) is not None


def include_commit(commit_text, all_commits):
    if commit_text.lower().startswith("merge"):
        return False
    if all_commits:
        return True
    if any(has_issue_link(commit_text, key) for key in project_keys):
        return True
    return False


def get_changelog(revision, all_commits):
    changelog = execute_command("git log --pretty=format:%s%n {}..{}".format(target_branch, revision))

    changes = sorted(set(changelog.split('\n\n')))
    changes = [x.strip('\n').replace('"', '\'') for x in changes
        if x and (include_commit(x, all_commits))]

    header = get_header(revision, target_branch)
    if changes:
        changes.insert(0, header)
    else:
        return header

    return '\n'.join(changes).strip('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', type=str, help="Target branch (where we should merge)")
    parser.add_argument('-r', '--rev', type=str, help="Source revision (from where we should merge)")
    parser.add_argument('-p', '--preview', action='store_true', help="preview changes, don't merge")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-a', '--all-commits', action='store_true', help="add all commits to changelog")
    args = parser.parse_args()

    global verbose
    verbose = args.verbose
    current_branch = get_current_branch()

    global target_branch
    if args.target:
        target_branch = args.target
    else:
        target_branch = current_branch

    revision = args.rev
    if not revision:
        revision = current_branch

    changelog = get_changelog(revision, args.all_commits)

    if args.preview:
        print(changelog)
        return 0

    execute_command("git checkout " + target_branch)
    execute_command("git merge --no-ff -m ", [changelog, revision])
    execute_command("git checkout " + current_branch)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        print("Command '{}' execution failed with return code '{}'".format(' '.join(e.cmd), e.returncode))
        print("Command's output:")
        print(e.output)
        sys.exit(1)
