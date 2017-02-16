#!/bin/python2

import sys
import os
import argparse
import xml.etree.ElementTree as ET
from validation_rules import get_validation_rules, Levels

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)

critical = ['\t', '%1', '%2', '%3', '%4', '%5', '%6', '%7', '%8', '%9', '<b>', '<b/>']
warned = ['\n', '\t', '<html', '<b>', '<br>', '<b/>', '<br/>']
numerus = ['%n']
substitution = ['%1', '%2', '%3', '%4', '%5', '%6', '%7', '%8', '%9']

verbose = False
strict = False
language = None

def printCritical(text, context, filename):
    err(u'Context: {0}\n{1}'.format(context, text))

class ValidationResult():
    error = 0
    warned = 0
    unfinished = 0
    total = 0

def symbolText(symbol):
    if symbol == '\t':
        return '\\t'
    if symbol == '\n':
        return '\\n'
    return symbol

def checkSymbol(symbol, source, target, context, out):
    # Ignoring incomplete translations
    if not target:
        return True

    occurences = source.count(symbol)
    valid = target.count(symbol) == occurences
    if not valid:
        out(u'Invalid translation string, error on {0} count:\nContext: {1}\nSource: {2}\nTarget: {3}'
            .format(
                    symbolText(symbol),
                    context,
                    source, target))

    return valid

def checkText(source, target, context, result, index, hasNumerusForm):
    if source.startswith('Ctrl+') or source.startswith('Shift+') or source.startswith('Alt+'):
        if target and target != source:
            err(u'Invalid shortcut translation form \nContext: {0}\nSource: {1}\nTarget: {2}'.format(context, source, target))
            result.error += 1

    if source.startswith('<') or source.startswith('&lt;'):
        err(u'Untranslatable string? \nContext: {0}\nSource: {1}'.format(context, source))
        result.error += 1

    for symbol in numerus:
        isNumerus = source.count(symbol)
        if (isNumerus and not hasNumerusForm) or (hasNumerusForm and not isNumerus and index > 1):
            warn(u'Invalid numerus form \nContext: {0}\nSource: {1}'.format(context, source))
            result.warned += 1
            break
           
    for symbol in critical:
        if not checkSymbol(symbol, source, target, context, err):
            result.error += 1
            break

    # Check if %2 does not exist without %1
    hasPreviuosSubstitution = True
    for symbol in substitution:
        hasCurrentSubstitution = source.count(symbol) > 0
        if hasCurrentSubstitution and not hasPreviuosSubstitution:
            err(u'Invalid substitution form \nContext: {0}\nSource: {1}'.format(context, source))
            result.error += 1
            break
        hasPreviuosSubstitution = hasCurrentSubstitution

    if verbose:
        for symbol in warned:
            if not checkSymbol(symbol, source, target, context, warn):
                result.warned += 1
                break
            if not checkSymbol(symbol, source, '', context, warn):
                result.warned += 1
                break


    return result;

def validateXml(root, filename):
    result = ValidationResult()

    printAll = strict and 'en_US' in filename

    version = root.get('version')
    language = root.get('language')
    sourcelanguage = root.get('sourcelanguage')
    if sourcelanguage and sourcelanguage != 'en' and sourcelanguage != 'en_US':
        result.warned += 1
        warn(u'Source Language is {0}'.format(sourcelanguage))

    suffix = language + '.ts'
    if not filename.endswith(suffix):
        result.error += 1
        err(u'Invalid Locale code {0} for file {1}'.format(language, filename))

    for context in root:
        contextName = context.find('name').text
        for message in context.iter('message'):
            result.total += 1
            source = message.find('source')

            translation = message.find('translation')
            if translation.get('type') == 'unfinished':
                result.unfinished += 1

            if translation.get('type') == 'obsolete':
                continue
                
            for rule in get_validation_rules():
                if rule.valid(source.text, translation):
                    continue
                if rule.level() == Levels.CRITICAL:
                    result.error += 1
                    printCritical(rule.last_error_text(), contextName, filename)

            hasNumerusForm = False
            index = 0
            for numerusform in translation.iter('numerusform'):
                hasNumerusForm = True
                index = index + 1
                if not numerusform.text:
                    continue;
                result = checkText(source.text, numerusform.text, contextName, result, index, hasNumerusForm)

            if hasNumerusForm:
                forms = [numerusform for numerusform in translation.iter('numerusform') if numerusform.text]
                filled = len([numerusform for numerusform in translation.iter('numerusform') if numerusform.text])
                if filled > 0 and filled != index:
                    result.error += 1
                    err(u'Incomplete numerus translation:\nContext: {0}\nSource: {1}\nTarget: {2}'.format(contextName, source.text, translation.text))
                    err(u'Filled {0} of {1} numerus forms'.format(filled, index))

            if not hasNumerusForm:
                result = checkText(source.text, translation.text, contextName, result, index, hasNumerusForm)
                if printAll and translation.text and not (source.text == translation.text):
                    info(u'\n\nTranslation string:\nContext: {0}\nSource: {1}\nTarget: {2}'.format(contextName, source.text, translation.text))


    return result

def validate(path):
    name = os.path.basename(path)
    if verbose:
        info('Validating {0}...'.format(name))
    tree = ET.parse(path)
    root = tree.getroot()
    result = validateXml(root, name)

    if result.error > 0:
        err('{0}: {1} errors found'.format(name, result.error))

    if verbose:
        if result.unfinished > 0:
            warn('{0}: {1} of {2} translations are unfinished'.format(name, result.unfinished, result.total))
        else:
            green('{0}: ok'.format(name))

def validateProject(project, translationDir):
    entries = []

    for entry in os.listdir(translationDir):
        path = os.path.join(translationDir, entry)

        if (os.path.isdir(path)):
            continue;

        suffix = '.ts'
        if language:
            suffix = '_{0}{1}'.format(language, suffix)

        if (not path.endswith(suffix)):
            continue;

        if (not entry.startswith(project)):
            continue;

        entries.append(path)

    for path in entries:
        validate(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-s', '--strict', action='store_true', help="strict check en_US translation")
    parser.add_argument('-l', '--language', help="check only selected language")
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    global strict
    strict = args.strict

    global language
    language = args.language

    if args.color:
        init_color()

    rootDir = os.getcwd()

    projects = getTranslatableProjects()
    for project in projects:
        if verbose:
            info("Updating project " + str(project))
        projectDir = os.path.join(rootDir, project.path)
        translationDir = os.path.join(projectDir, 'translations')
        validateProject(project.name, translationDir)

    info("Validation finished.")


if __name__ == "__main__":
    main()