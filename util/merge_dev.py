#!/bin/python2
# -*- coding: utf-8 -*-

#Options:
#   -P preview (do not merge)
#   -t {target_branch} Merge current branch to target
#   -r {source_branch} Merge from source_branch to the current one

#Example:
#merge_dev.py -r prod_2.5 -P    //prod_2.5 to current branch merge preview
#merge_dev.py -r prod_2.5       //merge prod_2.5 to the current branch
#merge_dev.py -t prod_2.5       //merge current branch to prod_2.5 ()


import subprocess
import sys
import os
import argparse

targetBranch = '.';
verbose = False
mergeCommit = 'merge'

def getHeader(merged, current):
    return "Merge: {0} -> {1}".format(merged, current)

def getCurrentBranch():
    return subprocess.check_output(['hg', 'branch']).strip('\n')

def execCommand(*command):
    if verbose:
        print command
    
    code = subprocess.call(command)
    if code != 0:
        print "Subprocess returned code {0}. Terminating...".format(code)
        sys.exit(code)
    return code
        
def getChangelog(revision):
    command = ['hg', 'log', '--template', '{desc}\n\n', '-r']
    changeset = ["(::{0} - ::{1})".format(revision, targetBranch)]
    command = command + changeset
    try:
        changelog = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError, e:
        print "Command {0} execution failed with return code {1}".format(e.cmd, e.returncode)
        print "Command's output:"
        print e.output
        return ''
    changes = sorted(set(changelog.split('\n\n')))
    changes = [x.strip('\n').replace('"', '\'') for x in changes if 
        x and not x.lower().startswith(mergeCommit)]

    if changes:
        changes.insert(0, getHeader(revision, targetBranch))
    else:
        return 'Merge Changelog is empty!'
    
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
       
    revision = args.rev
    if not revision:
        revision = '.'

    if revision == '.' and targetBranch != currentBranch:
        revision = currentBranch
        
    if args.preview:
        print getChangelog(revision)
        sys.exit(0)
   
    execCommand('hg', 'up', targetBranch)
    execCommand('hg', 'merge',  '--tool=internal:merge', revision)
    execCommand('hg', 'ci', '-m' + getChangelog(revision))
    execCommand('hg', 'up', currentBranch)
    sys.exit(0)
    
if __name__ == "__main__":
    main()
