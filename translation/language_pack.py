#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import shutil

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

verbose = False
targetFolder = None
kMinFileSize = 120

def copyFiles(project, filesByLang):
    for lang, files in filesByLang.items():
        if not files:
            err("Files not found for lang {0}".format(lang))
        targetDir = os.path.join(targetFolder, lang)
        targetDir = os.path.join(targetDir, project)
        if not os.path.isdir(targetDir):
            os.makedirs(targetDir)
        for file in files:
            shutil.copy(file, targetDir)


def calculateTsEntries(dir, prefix, extension, results):
    for entry in os.listdir(dir):
        if not entry.endswith(extension):
            continue
        if not entry.startswith(prefix):
            continue
        path = os.path.join(dir, entry)
        size = os.path.getsize(path)
        if size <= kMinFileSize:
            continue
        lang = entry[len(prefix):-len(extension)]
        if not lang in results:
            results[lang] = []
        results[lang].append(path)

# c++ translatable projects
def calculateTsFiles(rootDir, project):
    extension = '.ts'

    translationDir = os.path.join(rootDir, project.path, 'translations')
    files = dict()
    prefix = '{0}_'.format(project.name)
    calculateTsEntries(translationDir, prefix, extension, files)
    copyFiles(project.name, files)

# Old android client
def calculateXmlFiles(rootDir):
    extension = '.xml'
    prefix = 'translatable_'
    dirPrefix = 'values-'
    project = 'android-client'
    projectDir = os.path.join(rootDir, project)
    resourcesDir = os.path.join(os.path.join(projectDir, 'android-main'), 'maven')
    files = dict()
    for dirname, dirnames, filenames in os.walk(resourcesDir):
        for filename in filenames:
            if not filename.startswith(prefix):
                continue
            if not filename.endswith(extension):
                continue
            entry = os.path.join(dirname, filename)
            lang = os.path.basename(dirname)[len(dirPrefix):]
            if len(lang) == 0:
                lang = 'en_US'
            lang = lang.replace('-r', '_')
            if not lang in files:
                files[lang] = []
            files[lang].append(entry)
    copyFiles(project, files)

def calculateSources(rootDir, project):
    extension = '.ui'

    sourcesDir = os.path.join(rootDir, project.path, 'src')

    filesByDir = dict()
    cut = len(sourcesDir) + 1
    for dirname, dirnames, filenames in os.walk(sourcesDir):
        for filename in filenames:
            if not filename.endswith(extension):
                continue
            entry = os.path.join(dirname, filename)
            dir = dirname[cut:]
            if not dir in filesByDir:
                filesByDir[dir] = []
            filesByDir[dir].append(entry)

    for lang in os.listdir(targetFolder):
        packDir = os.path.join(targetFolder, lang)
        srcDir = os.path.join(packDir, 'src')
        for subdir, files in filesByDir.items():
            dir = os.path.join(srcDir, subdir)
            if not os.path.isdir(dir):
                os.makedirs(dir)
            for file in files:
                shutil.copy(file, dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-l', '--language', help="target language")
    parser.add_argument('-t', '--target', help="target folder")
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    global targetFolder
    targetFolder = args.target
    if not targetFolder:
        targetFolder = os.path.join(os.getcwd(), 'language_packs')
    #os.makedirs(targetFolder)

    rootDir = os.getcwd()
    projects = getTranslatableProjects()   
    for project in projects:
        calculateTsFiles(rootDir, project)
        #calculateXmlFiles(rootDir)
        calculateSources(rootDir, project)

if __name__ == "__main__":
    main()
