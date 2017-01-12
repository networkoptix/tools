#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import argparse
import os
from itertools import combinations
from customization import Customization
from sources_parser import parse_sources_cached, clear_sources_cache

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getCustomizableProjects
sys.path.pop(0)

verbose = False

class Intro:
    CLIENT = "client"
    FILES = {"intro.mkv", "intro.avi", "intro.png", "intro.jpg", "intro.jpeg"}

    @staticmethod
    def validate(customization):
        if customization.project.name == Intro.CLIENT:
            return len(customization.icons & Intro.FILES) == 1
        return True

    @staticmethod
    def isIntro(customization, icon):
        return customization.project.name == Intro.CLIENT and icon in Intro.FILES

def requiredFileKey(icon, prefix):
    key = icon
    if prefix and prefix in key:
        key = key.replace(prefix, "")
    while key.startswith("/"):
        key = key[1:]
    return key

def output(customization, text, func):
    if verbose:
        func(text)
    else:
        func('{0}:{1}: {2}'.format(customization.project.name, customization.name, text))

def printError(customization, text):
    output(customization, text, err)

def printWarning(customization, text):
    output(customization, text, warn)

def validateCustomization(customization):
    if verbose:
        info('Customization: ' + customization.name)
    for duplicate in customization.duplicates:
        printError(customization, "Duplicate file {0}".format(duplicate))

    if not Intro.validate(customization):
        printError(customization, "Intro is not found")

    for base, source in customization.baseIcons():
        if not base in customization.icons:
            printError(customization, "Base icon {0} for {1} is not found".format(base, source))

def validateRequiredFiles(customization, requiredFiles):
    if not requiredFiles:
        return

    prefix = customization.project.prefix

    for icon, location in requiredFiles:
        key = requiredFileKey(icon, prefix)
        if Intro.isIntro(customization, key):
            continue
        if not key in customization.icons:
            if verbose:
                printError(customization, "Icon {0} (key {1}) is not found (used in {2})".format(icon, key, location))
            else:
                printError(customization, "Icon {0} is not found".format(icon))

def validateUnusedFiles(customization, requiredFiles):
    if not requiredFiles:
        return

    prefix = customization.project.prefix
    keys = set()
    for icon, location in requiredFiles:
        keys.add(requiredFileKey(icon, prefix))

    base = set()
    for icon, source in customization.baseIcons():
        base.add(icon)

    for unused in base - keys:
        printWarning(customization, "Unused icon {0}".format(unused))

def crossCheckCustomizations(first, second):
    if verbose:
        info('Compare: ' + first.name + ' vs ' + second.name)
    for icon in first.icons - second.icons:
        if Intro.isIntro(first, icon):
            continue
        printError(first, "Icon {0} is missing in {1}".format(icon, second.name))
    for file in first.other_files - second.other_files:
        printError(first, "File {0} is missing in {1}".format(file, second.name))

def checkProject(rootDir, project):
    if verbose:
        separator()
        info("Validating project " + project.name)
    roots = []

    requiredFiles = None
    if project.sources:
        requiredFiles = []
        for dir in project.sources:
            requiredFiles += parse_sources_cached(os.path.join(rootDir, dir))

    customizationDir = os.path.join(rootDir, "customization")

    for entry in os.listdir(customizationDir):
        if (entry[:1] == '_'):
            continue
        path = os.path.join(customizationDir, entry)
        if (not os.path.isdir(path)):
            continue
        c = Customization(entry, path, project)
        if not c.supported:
            if verbose:
                info('Skip unsupported customization {0}'.format(c.name))
            continue

        validateCustomization(c)
        if c.isRoot():
            roots.append(c)
            validateRequiredFiles(c, requiredFiles)
            validateUnusedFiles(c, requiredFiles)

    for c1, c2 in combinations(roots, 2):
        crossCheckCustomizations(c1, c2)
        crossCheckCustomizations(c2, c1)
    if verbose:
        info('Validation finished')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('--clear-cache', action='store_true', help="Force clear sources cache")
    args = parser.parse_args()
    if args.color:
        init_color()

    if args.clear_cache:
        clear_sources_cache()

    global verbose
    verbose = args.verbose

    rootDir = os.getcwd()
    projects = getCustomizableProjects()

    for project in projects:
        checkProject(rootDir, project)

if __name__ == "__main__":
    main()
    sys.exit(0)