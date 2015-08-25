# -*- coding: utf-8 -*-
#/bin/python

import subprocess
import sys
import os
import argparse

targetBranch = '.';
ignoredCommits = ['Merge', '']
verbose = False
header = 'Merge Changelog:'

def getCurrentBranch():
    command = 'hg branch'
    return subprocess.check_output(command, shell=True).strip('\n')

def execCommand(command):
    if verbose:
        print command
    
    code = subprocess.call(command)
    if code != 0:
        sys.exit(code)
    return code
        
def getChangelog(revision):
    command = 'hg log -T "{desc}\\n\\n" -r '
    changeset = '"(::{0} - ::{1})"'.format(revision, targetBranch)
    command = command + changeset
    changelog = subprocess.check_output(command, shell=True)
    changes = sorted(set(changelog.split('\n\n')))
    changes = [x.strip('\n').replace('"', '\'') for x in changes if 
        not x in ignoredCommits and not x.startswith(header)]
    
    changes.insert(0, 'Merge Changelog:')
    
    return '\n'.join(changes).strip('\n')
      
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', type=str, help="Target branch")
    parser.add_argument('-r', '--rev', type=str, help="Source revision")
    parser.add_argument('-p', '--preview', action='store_true', help="preview changes")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
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
    
    ignoredCommits.append('Merge with {0}'.format(targetBranch))
    
    revision = args.rev
    if not revision:
        revision = '.'
   
    if args.preview:
        print getChangelog(revision)
        sys.exit(0)
   
    if revision == '.' and targetBranch != currentBranch:
        revision = currentBranch
   
    execCommand('hg up {0}'.format(targetBranch))
    execCommand('hg merge  --tool=internal:merge {0}'.format(revision))
    execCommand('hg ci -m"{0}"'.format(getChangelog(revision)))
    execCommand('hg up {0}'.format(currentBranch))
    sys.exit(0)
    
if __name__ == "__main__":
    main()
