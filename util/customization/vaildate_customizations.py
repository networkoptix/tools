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

def validateCustomization(customization):
    info('Customization: ' + customization.name)
    for duplicate in customization.duplicates:
        err("Duplicate file {0}".format(duplicate))

    if not Intro.validate(customization):
        err("Intro is not found")

    for base, source in customization.baseIcons():
        if not base in customization.icons:
            err("Base icon {0} for {1} is not found".format(base, source))

def validateRequiredFiles(customization, requiredFiles):
    prefix = customization.project.prefix

    for icon, location in requiredFiles:
        key = icon
        if prefix and prefix in key:
            key = key.replace(prefix, "")
        while key.startswith("/"):
            key = key[1:]
        if Intro.isIntro(customization, key):
            continue
        if not key in customization.icons:
            err("Icon {0} (key {1}) is not found (used in {2})".format(icon, key, location))

def crossCheckCustomizations(first, second):
    info('Compare: ' + first.name + ' vs ' + second.name)


def checkProject(rootDir, project):
    separator()
    info("Validating project " + project.name)
    roots = []

    requiredFiles = []
    if project.sources:
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

    for c1, c2 in combinations(roots, 2):
        crossCheckCustomizations(c1, c2)
        crossCheckCustomizations(c2, c1)
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