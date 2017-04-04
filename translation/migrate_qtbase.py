#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import xml.etree.ElementTree as ET
from shutil import copyfile

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

verbose = False

class MigrationResult():
    migrated = 0
    total = 0
    skipped = 0

class ExistingTranslation():
    context = ""
    source = ""
    translation = ""
    comment = ""

def existingTranslations(source_root):
    result = []
    for context in source_root:
        context_name = context.find('name').text
        for message in context.iter('message'):
            source = message.find('source')
            translation = message.find('translation')
            if not translation.text:
                continue
                
            comment = message.find('translatorcomment')

            t = ExistingTranslation()
            t.context = context_name
            t.source = source.text
            t.translation = translation.text
            if comment is not None:
                t.comment = comment.text
            result.append(t)

    return result

def findBestTranslation(context, source, existing):
    best = None
    for t in existing:
        if t.source != source:
            continue
        if t.context == context:
            return t
        best = t
    return best

def migrateXml(source_root, target_root, language):
    translations = existingTranslations(source_root)
    result = MigrationResult()
    target_root.set('language', language)
    for context in target_root:
        context_name = context.find('name').text
        for message in context.iter('message'):
            source = message.find('source')
            translation = message.find('translation')
            result.total += 1

            existing = findBestTranslation(context_name, source.text, translations)
            if not existing:
                result.skipped += 1
                continue

            translation.text = existing.translation
            translation.attrib.pop("type", None)
            if existing.comment:
                comment = ET.SubElement(message, 'translatorcomment')
                comment.text = existing.comment
                
            if verbose:
                info(u"{0}\t ->{1}".format(source.text, existing.translation))
            result.migrated += 1
    return result

def migrateFile(existing_file, target_file, language):
    target_tree = ET.parse(target_file)
    target_root = target_tree.getroot()

    source_tree = ET.parse(existing_file)
    source_root = source_tree.getroot()

    result = migrateXml(source_root, target_root, language)
    if verbose:
        info("{0} items processed".format(result.total))
    if result.migrated > 0:
        info("{0} items migrated".format(result.migrated))
        with open(target_file, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE TS>\n')
            target_tree.write(f, 'utf-8')
#        target_tree.write(target_file, encoding="utf-8", xml_declaration=True)
    if result.skipped > 0:
        warn('{0} items were not translated'.format(result.skipped))

def main():
    parser = argparse.ArgumentParser(description='''
    This script migrates existing qtbase translations from the Qt 5.2 to Qt 5.6 format.''')
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-l', '--language', help="language", required=True)
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    info("Starting process for language {0}".format(args.language))

    rootDir = os.getcwd()
    source_file = os.path.join(rootDir, 'qtbase.xml')
    existing_file = os.path.join(rootDir, 'qtbase_{0}.xml'.format(args.language))
    target_file = os.path.join(rootDir, 'qtbase_{0}.ts'.format(args.language))

    if verbose:
        info("Renaming {0} to {1}".format(target_file, existing_file))
    if os.path.isfile(existing_file):
        os.unlink(existing_file)
    os.rename(target_file, existing_file)

    if verbose:
        info("Copying {0} to {1}".format(source_file, target_file))
    copyfile(source_file, target_file)

    if verbose:
        info("Generating {0} from {1}".format(target_file, existing_file))
    migrateFile(existing_file, target_file, args.language)
    
    if verbose:
        info("Cleanup {0}".format(existing_file))
    os.unlink(existing_file)

    if verbose:
        info("Migration finished.")


if __name__ == "__main__":
    main()