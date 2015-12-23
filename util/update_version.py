#!/bin/python2
# -*- coding: utf-8 -*-

import fileinput
import os
import sys
import argparse
import re
from common_module import init_color,info,green,warn,err

filePattern = "pom.xml"
versionPattern = "<version>{0}-SNAPSHOT</version>"

def getCurrentVersion():
    rootDir = os.getcwd()  
    regexp = re.compile("<version>(.*)-SNAPSHOT</version>")
    
    rootFile = os.path.join(rootDir, filePattern)
    with open(rootFile, 'r') as source_file:
        for line in source_file:
            match = regexp.search(line)
            if match:
                return match.group(1)
    raise Exception('Source version cannot be detected')

def updateVersion(old_version, new_version, filename, preview):
    counter = 0
    info("Checking file {0}".format(filename))
    for line in fileinput.input(filename, inplace=1):       
        if old_version in line:
            counter += 1
            if not preview:
                line = line.replace(old_version,new_version)
        sys.stdout.write(line)
    fileinput.close()
    if counter > 0:
        warn('Updated file {0}'.format(filename))

def updateVersionRecursive(old_version, new_version, preview):
    rootDir = os.getcwd()

    old_version_text = versionPattern.format(old_version)
    new_version_text = versionPattern.format(new_version)
    
    info('Updating version {0} to {1}'.format(old_version_text, new_version_text))
    if preview:
        warn("Preview mode")
    
    for path, subdirs, files in os.walk(rootDir):
        if '.hg' in subdirs:
            subdirs.remove('.hg')
        if filePattern in files:
            updateVersion(old_version_text, new_version_text, os.path.join(path, filePattern), preview)

def main():      

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-s', '--source', type=str, help="Source version", default = getCurrentVersion())
    parser.add_argument('-t', '--target', type=str, help="Target version", required = True)
    parser.add_argument('-p', '--preview', action='store_true', help="preview changes")
    args = parser.parse_args()
    
    if args.color:
        init_color()
    
    updateVersionRecursive(args.source, args.target, args.preview)   

if __name__ == "__main__":
    main()