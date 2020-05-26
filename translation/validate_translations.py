#!/usr/bin/env python3

import argparse
import os
import sys
import xml.etree.ElementTree as ET

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color, info, warn, err
sys.path.pop(0)

rulesDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'rules')
sys.path.insert(0, rulesDir)
from validation_rule import Levels, ValidationRule
from rules_list import get_validation_rules
sys.path.pop(0)

if os.path.isfile('current_config.py'):
    sys.path.insert(0, os.getcwd())
    from current_config import PROJECT_SOURCE_DIR

    if '$' not in PROJECT_SOURCE_DIR:
        os.chdir(PROJECT_SOURCE_DIR)
    sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/validation')
sys.path.insert(0, projectDir)
from translatable_projects import get_translatable_projects
sys.path.pop(0)


def print_leveled(text, level):
    if level == Levels.CRITICAL:
        err(text)
    elif level == Levels.WARNING:
        warn(text)
    else:
        info(text)
    print('')


def validate_xml(root, filename, lowest_level):
    applied_rules = list(get_validation_rules(filename))

    diagnostics = []

    for context in root:
        contextName = context.find('name').text
        for message in context.iter('message'):
            for rule in applied_rules:
                if rule.level() < lowest_level:
                    continue
                if not rule.valid_message(contextName, message):
                    source = ValidationRule.translation_source(message)
                    diagnostics.append((contextName, source, rule.last_error_text(), rule.level()))

    if diagnostics:
        max_level = max(diagnostics, key=lambda x: x[3])
        print_leveled(u"\nValidating {}...".format(filename), max_level[3])
        for context, source, text, level in diagnostics:
            message = u'*** Context: {0} ***\n*** Source: {1}\n{2}'.format(context, source, text)
            print_leveled(message, level)


def validate_file(path, lowest_level):
    name = os.path.basename(path)
    tree = ET.parse(path)
    root = tree.getroot()
    validate_xml(root, name, lowest_level)


def calculate_files(project, translations_dir, language):
    for entry in os.listdir(translations_dir):
        path = os.path.join(translations_dir, entry)

        if os.path.isdir(path):
            continue

        suffix = '.ts'
        if language:
            suffix = '_{0}{1}'.format(language, suffix)

        if not path.endswith(suffix):
            continue

        if not entry.startswith(project):
            continue

        yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="Colorized output")
    parser.add_argument('-e', '--errors-only', action='store_true', help="Show only errors")
    parser.add_argument('-w', '--warnings', action='store_true', help="Show warnings and errors")
    parser.add_argument('-l', '--language', help="Check only selected language")
    parser.add_argument(
        '-p', '--project', help="Check only selected project. Allowed values: mobile, vms.")
    args = parser.parse_args()

    if args.color:
        init_color()

    rootDir = os.getcwd()

    files = []
    projects = get_translatable_projects(args.project)
    for project in projects:
        projectDir = os.path.join(rootDir, project.path)
        translations_dir = os.path.join(projectDir, 'translations')
        files += list(calculate_files(project.name, translations_dir, args.language))

    lowest_level = Levels.INFO
    if args.warnings:
        lowest_level = Levels.WARNING
    if args.errors_only:
        lowest_level = Levels.CRITICAL

    files.sort(key=lambda filename: filename[-8:-3])
    for file in files:
        validate_file(file, lowest_level)

    info("Validation finished.")


if __name__ == "__main__":
    main()
