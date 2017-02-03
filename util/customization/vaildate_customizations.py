#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import argparse
import os
from itertools import combinations
from customization import Customization, readConfig
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

DEFAULT = "default"

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
    projectName = customization.project.name if customization.project else ""
    if verbose:
        func(text)
    else:
        func('{0}:{1}: {2}'.format(projectName, customization.name, text))

def printError(customization, text):
    output(customization, text, err)

def printWarning(customization, text):
    output(customization, text, warn)

def validateCustomization(customization, requiredFiles):
    if verbose:
        info('Customization: ' + customization.name)
    for duplicate in customization.duplicates:
        printError(customization, "Duplicate file {0}".format(duplicate))

    if not Intro.validate(customization):
        printError(customization, "Intro is not found")

    for base, source in customization.scaled_icons:
        if not base in customization.icons:
            printError(customization, "Base icon {0} for {1} is not found".format(base, source))

    for base, source in customization.baseIcons():
        if not base in customization.icons:
            # Check if we are directly using suffixed icon
            if requiredFiles and source in requiredFiles:
                continue
            printError(customization, "Base icon {0} for {1} is not found".format(base, source))

def validateRequiredFiles(customization, requiredFiles):
    if not requiredFiles:
        return

    scaled_sources = set([source for base, source in customization.scaled_icons])

    for key, value in requiredFiles.items():
        if Intro.isIntro(customization, key):
            continue
        icon, location = value
        if not key in customization.icons and not key in scaled_sources:
            if verbose:
                printError(customization, "Icon {0} (key {1}) is not found (used in {2})".format(icon, key, location))
            else:
                printError(customization, "Icon {0} for {1} is not found".format(icon, location))

def validateUnusedFiles(customization, requiredFiles, specificFiles):
    if not requiredFiles:
        return

    for icon, source in customization.baseIcons():
        if not icon in requiredFiles and not source in requiredFiles and not source in specificFiles:
            printWarning(customization, "Unused icon {0}".format(source))

def crossCheckCustomizations(first, second):
    if verbose:
        info('Compare: ' + first.name + ' vs ' + second.name)

    for icon in first.icons - second.icons:
        if Intro.isIntro(first, icon):
            continue
        folder, sep, path = icon.partition("/")
        if folder in second.skipped:
            continue
        printError(second, "Icon {0} is missing".format(icon))

    for file in first.other_files - second.other_files:
        printError(second, "File {0} is missing".format(file))

def checkProject(rootDir, project):
    if verbose:
        separator()
        info("Validating project " + project.name)
    roots = []
    unparented = []
    default = None

    prefix = project.prefix

    requiredFiles = None
    if project.sources:
        requiredFiles = {} # Map of key -> tuple (icon, location)
        for dir in project.sources:
            for icon, location in parse_sources_cached(os.path.join(rootDir, dir)):
                key = requiredFileKey(icon, prefix)
                # ignoring additional locations of an icon
                if key in requiredFiles:
                    continue
                requiredFiles[key] = (icon, location)

    customizationDir = os.path.join(rootDir, "customization")

    for entry in os.listdir(customizationDir):
        path = os.path.join(customizationDir, entry)
        if (not os.path.isdir(path)):
            continue
        c = Customization(entry, path, project)
        if DEFAULT == entry:
            default = c

        if not c.supported:
            if verbose:
                info('Skip unsupported customization {0}'.format(c.name))
            continue

        specificFiles = set()
        for icon, location in c.specific_icons:
            specificFiles.add(requiredFileKey(icon, prefix))

        validateCustomization(c, requiredFiles)
        if c.isRoot():
            roots.append(c)
            validateRequiredFiles(c, requiredFiles)
            validateUnusedFiles(c, requiredFiles, specificFiles)
        elif project.ignore_parent:
            unparented.append(c)

    for c1, c2 in combinations(roots, 2):
        crossCheckCustomizations(c1, c2)
        crossCheckCustomizations(c2, c1)

    for c2 in unparented:
        crossCheckCustomizations(default, c2)

    if verbose:
        info('Validation finished')

def validateBuildProperties(rootDir):
    if verbose:
        separator()
        info("Validating build properties")

    customizationDir = os.path.join(rootDir, "customization")

    defaultValues = readConfig(os.path.join(customizationDir, 'default-values.properties'))

    customizations = []
    default = None

    for entry in os.listdir(customizationDir):
        path = os.path.join(customizationDir, entry)
        if (not os.path.isdir(path)):
            continue

        c = Customization(entry, path, None)
        if DEFAULT == entry:
            default = c
        else:
            customizations.append(c)

    for c in customizations:
        if not c.supported:
            if verbose:
                info('Skip unsupported customization {0}'.format(c.name))
            continue

        if verbose:
            info('Customization: {0}'.format(c.name))
        for key in default.build_properties:
            if key in defaultValues:
                continue

            section, sep, name = key.partition(".")
            if section == "ax" and "paxton" in c.skipped:
                continue
            if section == "android" and "android" in c.skipped:
                continue
            if section == "ios" and "ios" in c.skipped:
                continue

            if not key in c.build_properties:
                printError(c, "Property {0} is missing".format(key))

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
    validateBuildProperties(rootDir)

    projects = getCustomizableProjects()
    for project in projects:
        checkProject(rootDir, project)

if __name__ == "__main__":
    main()
    sys.exit(0)