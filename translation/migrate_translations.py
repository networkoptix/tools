#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import difflib
import os
import sys
import xml.etree.ElementTree as ET

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color, info, warn, err
sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)


verbose = False
similarityLevel = 100

ignored = ['Ctrl+', 'Shift+', 'Alt+']


class MigrationResult:
    migrated = 0
    total = 0


def calcDistance(l, r):
    return (1.0 - difflib.SequenceMatcher(a=l.lower(), b=r.lower()).ratio()) * 1000


def findSimilar(text, existing):
    minDistance = 0xFFFF
    result = None

    for s in existing:
        distance = calcDistance(text, s)
        if distance < minDistance and distance <= similarityLevel:
            minDistance = distance
            result = s

    return result


def existingTranslations(context):
    result = {}
    for message in context.iter('message'):
        if message.get('numerus') == 'yes':
            continue

        source = message.find('source')
        translation = message.find('translation')
        if not translation.text:
            continue

        if translation.get('type') == 'obsolete':
            continue

        if any(s in source.text for s in ignored):
            continue

        result[source.text] = translation.text

    return result


def migrateXml(root, sourceRoot):
    result = MigrationResult()
    for context in root:
        contextName = context.find('name').text

        filter = "./context[name='{}']".format(contextName)
        sourceContexts = sourceRoot.findall(filter)
        if len(sourceContexts) != 1:
            if verbose:
                warn("Context {0} not found".format(contextName))
            continue
        sourceContext = sourceContexts[0]
        sourceTranslations = existingTranslations(sourceContext)

        for message in context.iter('message'):
            if message.get('numerus') == 'yes':
                continue

            source = message.find('source')
            translation = message.find('translation')

            if translation.text:
                continue

            if translation.get('type') == 'obsolete':
                continue

            result.total += 1

            existing = findSimilar(source.text, sourceTranslations.keys())
            if not existing:
                continue

            existingTranslation = sourceTranslations[existing]
            translation.text = existingTranslation
            if verbose:
                info("{0}\t ->{1}".format(source.text, existing))

            result.migrated += 1

    return result


def migrateFile(path, sourcePath):
    name = os.path.basename(path)
    if verbose:
        info("Migrating {0} from {1}".format(name, sourcePath))

    tree = ET.parse(path)
    root = tree.getroot()

    sourceTree = ET.parse(sourcePath)
    sourceRoot = sourceTree.getroot()

    result = migrateXml(root, sourceRoot)
    if verbose:
        info("{0} items processed".format(result.total))
    if result.migrated > 0:
        warn("{0} items migrated to {1}".format(result.migrated, name))
        tree.write(path, encoding="utf-8", xml_declaration=True)
    elif verbose:
        info("{0} items migrated".format(result.migrated))


def migrateProject(project, translationDir, sourceTranslationDir):
    entries = {}

    for entry in os.listdir(translationDir):
        path = os.path.join(translationDir, entry)

        if os.path.isdir(path):
            continue

        if not path[-2:] == 'ts':
            continue

        if not entry.startswith(project):
            continue

        if 'en_US' in entry:
            continue

        sourcePath = os.path.join(sourceTranslationDir, entry)
        if not os.path.isfile(sourcePath):
            err("{0} not found in the source dir {1}".format(entry, sourceTranslationDir))
            continue

        entries[path] = sourcePath

    for path, sourcePath in entries.items():
        migrateFile(path, sourcePath)


def main():
    parser = argparse.ArgumentParser(description='''
    This script migrates existing translations from the version of code before the lupdate call.
    To implement this you should have two copies of the repository. Target repo root is the call
    folder. Source repo root is passed as the 'source' argument.
    ''')
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-s', '--source', help="source path", required=True)
    parser.add_argument('-l', '--level', help="similarity level", type=int)
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    if args.level:
        global similarityLevel
        similarityLevel = args.level
    info("Starting process with similarity level {0}".format(similarityLevel))

    rootDir = os.getcwd()

    projects = getTranslatableProjects()
    for project in projects:
        if verbose:
            info("Updating project " + str(project))
        projectDir = os.path.join(rootDir, project.path)
        sourceProjectDir = os.path.join(args.source, project.path)

        translationDir = os.path.join(projectDir, 'translations')
        sourceTranslationDir = os.path.join(sourceProjectDir, 'translations')

        migrateProject(project.name, translationDir, sourceTranslationDir)

    if verbose:
        info("Migration finished.")


if __name__ == "__main__":
    main()
