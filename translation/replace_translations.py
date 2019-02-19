# -*- coding: utf-8 -*-
#/bin/python

import os
import sys
import argparse
import string
import xml.etree.ElementTree as ET

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

from vms_projects import getTranslatableProjectsList

allowedSrcExtensions = ['.cpp', '.h', '.ui', '.qml']
ignoredFiles = ['translation_manager.cpp']
ignoredContexts = ['Language']

verbose = False


class ReplaceItemStruct():
    def __init__(self, initContext, initSource, initTarget):
        self.context = initContext
        self.source = initSource
        self.target = initTarget

    def __str__(self):
        return 'Context: {0}\nSource:\t{1}\nTarget:\t{2}\n'.format(self.context, self.source, self.target)

    def isValid(self):
        return self.source != self.target


def extractReplaces(root):
    result = []

    for context in root:
        contextName = context.find('name').text
        if contextName in ignoredContexts:
            continue

        for message in context.iter('message'):
            source = message.find('source')
            translation = message.find('translation')
            # if translation.get('type') == 'unfinished':
            #    continue

            if translation.get('type') == 'obsolete':
                continue

            # Using source text
            if not translation.text:
                continue

            hasNumerusForm = False
            index = 0
            for numerusform in translation.iter('numerusform'):
                hasNumerusForm = True
                index = index + 1
                if not numerusform.text:
                    continue

            if not hasNumerusForm:
                replaceItem = ReplaceItemStruct(contextName, source.text, translation.text)
                if replaceItem.isValid():
                    result.append(replaceItem)
                else:
                    warn("Invalid item:\n{0}".format(replaceItem))

    return result


def ReadFileText(fileName):
    fileEntry = open(fileName, 'r')
    text = fileEntry.read()
    fileEntry.close()
    return text


def WriteTextToFile(fileName, text):
    fileEntry = open(fileName, 'w')
    fileEntry.write(text)
    fileEntry.close()


def allowedEntry(entry):
    if entry in ignoredFiles:
        return False

    for ext in allowedSrcExtensions:
        if entry.endswith(ext):
            return True

    return False


def formatSearchString(entry, text):
    if entry.endswith('.ui'):
        return '<string>{0}'.format(text)
    return '"{0}"'.format(text)


def processReplaceItem(replaceItem, srcDir):
    for entry in os.listdir(srcDir):
        fullEntryPath = os.path.join(srcDir, entry)
        if os.path.isdir(fullEntryPath):
            if processReplaceItem(replaceItem, fullEntryPath):
                return True
            else:
                continue

        if not allowedEntry(entry):
            continue

        text = ReadFileText(fullEntryPath)
        if replaceItem.context not in text:
            continue

        source = formatSearchString(entry, replaceItem.source)
        if not (source) in text:
            continue

        target = formatSearchString(entry, replaceItem.target)

        newText = string.replace(text, source, target)
        WriteTextToFile(fullEntryPath, newText)

        if verbose:
            info('Replacing at path: {0}\n{1}\n'.format(fullEntryPath, replaceItem))
        return True

    return False


def validateProject(project, translationDir, srcDir):
    entries = []

    for entry in os.listdir(translationDir):
        translationPath = os.path.join(translationDir, entry)

        if (os.path.isdir(translationPath)):
            continue

        if ((not translationPath[-2:] == 'ts') or ('en_US' not in translationPath)):
            continue

        if (not entry.startswith(project)):
            continue

        entries.append(translationPath)

    replaceList = []
    for translationPath in entries:
        if verbose:
            info("Parsing file: {0}".format(translationPath))
        tree = ET.parse(translationPath)
        root = tree.getroot()
        replaceList.extend(extractReplaces(root))

    for replaceItem in replaceList:
        if not processReplaceItem(replaceItem, srcDir):
            err('Could not find:\n{0}'.format(replaceItem))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    rootDir = os.getcwd()

    for project in getTranslatableProjectsList():
        projectDir = os.path.join(rootDir, project)

        srcDir = os.path.join(projectDir, 'src')
        translationDir = os.path.join(projectDir, 'translations')
        validateProject(project, translationDir, srcDir)

    if verbose:
        info('Finished.')


if __name__ == "__main__":
    main()
