#!/usr/bin/env python3

"""
NOTE: This script will be deleted when migration from 
mercurial will be finished.

Options:
   -P preview (do not merge)
   -t {target_branch} Merge current branch to target
   -r {source_branch} Merge from source_branch to the current one

Example:
merge_dev.py -r prod_2.5 -P    //prod_2.5 to current branch merge preview
merge_dev.py -r prod_2.5       //merge prod_2.5 to the current branch
merge_dev.py -t prod_2.5       //merge current branch to prod_2.5 ()
"""

import subprocess
import sys
import os
import argparse
import re

import merge_dev_git

targetBranch = '.';
mergeCommit = 'merge'
projectKeys = ['VMS', 'UT', 'CP', 'CLOUD', 'PSP', 'DESIGN', 'ENV', 'FR', 'HNW', 'LIC', 'MOBILE',
    'META', 'NCD', 'NXPROD', 'NXTOOL', 'STATS', 'CALC', 'TEST', 'VISTA', 'WEB', 'WS']

def print_command(command):
    print('>> {0}'.format(subprocess.list2cmdline(command)))

def execute_command(command, verbose = False):
    if verbose:
        print_command(command)
    try:
        subprocess.check_output(command, stderr = subprocess.STDOUT)
    except Exception as e:
        if not verbose:
            print_command(command)
        print("Error: {0}".format(e.output))
        raise

def is_inside_mercurial():
    if os.path.isdir('.hg'):
        return True

    try:
        return "true" == merge_dev_git.execute_command("hg id")
    except subprocess.CalledProcessError as e:
        return False

def getHeader(merged, current):
    return "Merge: {0} -> {1}".format(merged, current)

def getCurrentBranch():
    return subprocess.check_output(['hg', 'branch'], universal_newlines=True).strip('\n')

def commandLine(command):
    return '>> ' + ' '.join(command).replace('\n', '\\n')

def hasIssueLink(commitText, projectKey):
    return re.search('([^_]|\A){0}-\d+'.format(projectKey.lower()), commitText.lower()) is not None

def includeCommit(commitText, all_commits):
    return (not commitText.lower().startswith(mergeCommit)
        and (all_commits or any(hasIssueLink(commitText, projectKey) for projectKey in projectKeys)))

def getChangelog(revision, multiline, verbose, all_commits):
    command = ['hg', 'log', '--template']
    if multiline:
        command += ['{desc}\n\n']
    else:
        command += ['{desc|firstline}\n\n']
    command += ['-r', "(::{0} - ::{1})".format(revision, targetBranch)]
    if verbose:
        print(commandLine(command))

    changelog = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)

    changes = sorted(set(changelog.split('\n\n')))
    changes = [x.strip('\n').replace('"', '\'') for x in changes
        if x and (includeCommit(x, all_commits))]

    header = getHeader(revision, targetBranch)
    if changes:
        changes.insert(0, header)
    else:
        return header

    return '\n'.join(changes).strip('\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', type=str, help="Target branch")
    parser.add_argument('-r', '--rev', type=str, help="Source revision")
    parser.add_argument('-p', '--preview', action='store_true', help="preview changes")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-m', '--multiline', action='store_true', help="multiline changelog")
    parser.add_argument('-a', '--all-commits', action='store_true', help="add all commits to changelog")
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    currentBranch = getCurrentBranch()

    global targetBranch
    target = args.target
    if target:
        targetBranch = target
    else:
        targetBranch = currentBranch

    revision = args.rev
    if not revision:
        revision = '.'

    if revision == '.' and targetBranch != currentBranch:
        revision = currentBranch

    changelog = getChangelog(revision, args.multiline, args.verbose, args.all_commits)

    if args.preview:
        print(changelog)
        sys.exit(0)

    execute_command(['hg', 'up', targetBranch], verbose)
    execute_command(['hg', 'merge',  '--tool=internal:merge', revision], verbose)
    execute_command(['hg', 'ci', '-m' + changelog], verbose)
    execute_command(['hg', 'up', currentBranch], verbose)
    sys.exit(0)

def choose_vcs_function():
    if merge_dev_git.is_inside_git():
        return merge_dev_git.main
    elif is_inside_mercurial():
        return main
    else:
        raise RuntimeError("No version control system found!")

if __name__ == "__main__":
    try:
        merge = choose_vcs_function()
        merge()
    except subprocess.CalledProcessError as e:
        print("Command {0} execution failed with return code {1}".format(e.cmd, e.returncode))
        print("Command's output:")
        print(e.output)
        sys.exit(1)
