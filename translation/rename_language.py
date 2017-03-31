#/bin/python

import sys
import os
import argparse
import subprocess
import fileinput

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)

def move(source, target):
    command = ['hg', 'move', source, target]
    subprocess.check_output(command, stderr=subprocess.STDOUT)

def moveTranslations(rootDir, languageFrom, languageTo, dryrun):
    suffix = "_{0}.ts".format(languageFrom)    
    for project in getTranslatableProjects():
        projectDir = os.path.join(rootDir, project.path)
        translationDir = os.path.join(projectDir, 'translations')

        for entry in os.listdir(translationDir):
            source = os.path.join(translationDir, entry)
            if (not source.endswith(suffix)):
                continue;              
            target = source.replace(languageFrom, languageTo)
            if dryrun:
                print "{0} will be moved to {1}".format(source, target)
                continue
            move(source, target)

def moveFlag(rootDir, languageFrom, languageTo, dryrun):
    relPath = 'common/static-resources/flags/{0}.png'.format(languageFrom)
    source = os.path.join(rootDir, relPath)
    target = source.replace(languageFrom, languageTo)
    if dryrun:
        print "{0} will be moved to {1}".format(source, target)
    move(source, target)   

def fixCustomizations(rootDir, languageFrom, languageTo, dryrun):
    customizationsDir = os.path.join(rootDir, 'customization')
    files = ['customization.cmake', 'build.properties']
    
    for entry in os.listdir(customizationsDir):
        subdir = os.path.join(customizationsDir, entry)    
        if not os.path.isdir(subdir):
            continue
        for file in files:
            filePath = os.path.join(subdir, file)
            if not os.path.isfile(filePath):
                continue
            for line in fileinput.input(filePath, inplace=not dryrun):
                fix = 'translation' in line and languageFrom in line
                if dryrun and fix:
                    print 'Replacing language in file {0}'.format(filePath)
                    sys.stdout.write(line)
                    sys.stdout.write(line.replace(languageFrom, languageTo))
                if not dryrun:
                    sys.stdout.write(line.replace(languageFrom, languageTo) if fix else line)
                sys.stdout.flush()
        

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', help="source language", required=True)
    parser.add_argument('-t', '--target', help="target language", required=True)
    parser.add_argument('-d', '--dryrun', help="preview changes", action='store_true')
    args = parser.parse_args()

    moveTranslations(os.getcwd(), args.source, args.target, args.dryrun)
    moveFlag(os.getcwd(), args.source, args.target, args.dryrun)
    fixCustomizations(os.getcwd(), args.source, args.target, args.dryrun)
    print "ok"


if __name__ == "__main__":
    main()
