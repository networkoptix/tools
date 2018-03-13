#!/bin/python2

import sys
import os
import argparse
import xml.etree.ElementTree as ET

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color, info, green, warn, err
sys.path.pop(0)

rulesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rules')
sys.path.insert(0, rulesDir)
from validation_rule import Levels
from rules_list import get_validation_rules
sys.path.pop(0)

if os.path.isfile('current_config.py'):
    sys.path.insert(0, os.getcwd())
    from current_config import PROJECT_SOURCE_DIR
    os.chdir(PROJECT_SOURCE_DIR)
    sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)


def printLeveled(text, level):
    if level == Levels.CRITICAL:
        err(text)
    elif level == Levels.WARNING:
        warn(text)
    else:
        info(text)


def validateXml(root, filename, errorsOnly):
    applied_rules = list(get_validation_rules(filename))

    diagnostics = []

    for context in root:
        contextName = context.find('name').text
        for message in context.iter('message'):
            for rule in applied_rules:
                if errorsOnly and rule.level() != Levels.CRITICAL:
                    continue
                if not rule.valid_message(contextName, message):
                    diagnostics.append((contextName, rule.last_error_text(), rule.level()))

    if diagnostics:
        max_level = max(diagnostics, key=lambda x: x[2])
        printLeveled(u"\nValidating {}...".format(filename), max_level[2])
        for context, text, level in diagnostics:
            message = u'*** Context: {0} ***\n{1}'.format(context, text)
            printLeveled(message, level)


def validateFile(path, errorsOnly):
    name = os.path.basename(path)
    tree = ET.parse(path)
    root = tree.getroot()
    validateXml(root, name, errorsOnly)


def validateProject(project, translationDir, language, errorsOnly):
    entries = []

    for entry in os.listdir(translationDir):
        path = os.path.join(translationDir, entry)

        if (os.path.isdir(path)):
            continue

        suffix = '.ts'
        if language:
            suffix = '_{0}{1}'.format(language, suffix)

        if (not path.endswith(suffix)):
            continue

        if (not entry.startswith(project)):
            continue

        entries.append(path)

    for path in entries:
        validateFile(path, errorsOnly)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-e', '--errors-only', action='store_true', help="do not show warnings")
    parser.add_argument('-l', '--language', help="check only selected language")
    args = parser.parse_args()

    if args.color:
        init_color()

    rootDir = os.getcwd()

    projects = getTranslatableProjects()
    for project in projects:
        projectDir = os.path.join(rootDir, project.path)
        translationDir = os.path.join(projectDir, 'translations')
        validateProject(project.name, translationDir, args.language, args.errors_only)

    info("Validation finished.")


if __name__ == "__main__":
    main()
