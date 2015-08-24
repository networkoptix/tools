# -*- coding: utf-8 -*-
#/bin/python

import sys
import os
import argparse
import xml.etree.ElementTree as ET
from common_module import init_color,info,green,warn,err

projects = ['common', 'client', 'traytool']

critical = ['\t', '%1', '%2', '%3', '%4', '%5', '%6', '%7', '%8', '%9', 'href', '<html', '<b>', '<br>', '<b/>', '<br/>']
warned = ['\n', '\t', '<html', '<b>', '<br>', '<b/>', '<br/>']
numerus = ['%n']

verbose = False
noTarget = False
strict = False

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
    occurences = source.count(symbol)
    invalid = target.count(symbol) != occurences
    if invalid and noTarget:
        out(u'Invalid translation string, error on {0} count:\nContext: {1}\nSource: {2}'
            .format(
                    symbolText(symbol),
                    context,
                    source))
    elif invalid:
        out(u'Invalid translation string, error on {0} count:\nContext: {1}\nSource: {2}\nTarget: {3}'
            .format(
                    symbolText(symbol),
                    context,
                    source, target))    
        
    return invalid
    
def checkText(source, target, context, result, index):

    for symbol in critical:
        if checkSymbol(symbol, source, target, context, err):
            result.error += 1
            break
    
    if (index != 1):
        for symbol in numerus:
            if checkSymbol(symbol, source, target, context, err):
                result.error += 1
                break
    
    if verbose:
        for symbol in warned:
            if checkSymbol(symbol, source, target, context, warn):
                result.warned += 1
                break
            if checkSymbol(symbol, source, '', context, warn):
                result.warned += 1
                break             
            

    return result;

def validateXml(root, name):
    result = ValidationResult()
       
    printAll = strict and 'en_US' in name
    
    for context in root:
        contextName = context.find('name').text
        for message in context.iter('message'):
            result.total += 1
            source = message.find('source')
            translation = message.find('translation')
            if translation.get('type') == 'unfinished':
                result.unfinished += 1
                continue
            
            if translation.get('type') == 'obsolete':
                continue

            #Using source text
            if not translation.text:
                continue

            hasNumerusForm = False
            index = 0
            for numerusform in translation.iter('numerusform'):
                hasNumerusForm = True
                index = index + 1
                if not numerusform.text:
                    continue;
                result = checkText(source.text, numerusform.text, contextName, result, index)
                
            if not hasNumerusForm:
                result = checkText(source.text, translation.text, contextName, result, index)
                if printAll and not (source.text == translation.text):
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

    if result.unfinished > 0:
        warn('{0}: {1} of {2} translations are unfinished'.format(name, result.unfinished, result.total))
    elif verbose:
        green('{0}: ok'.format(name))

def validateProject(project, translationDir):
    entries = []

    for entry in os.listdir(translationDir):
        path = os.path.join(translationDir, entry)
        
        if (os.path.isdir(path)):
            continue;
                
        if (not path[-2:] == 'ts'):
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
    parser.add_argument('-t', '--no-target', action='store_true', help="skip target field")
    parser.add_argument('-s', '--strict', action='store_true', help="strict check en_US translation")
    args = parser.parse_args()
    
    global verbose
    verbose = args.verbose
    
    global noTarget
    noTarget = args.no_target
    
    global strict
    strict = args.strict
    
    if args.color:
        init_color()

    rootDir = os.getcwd()
    
    for project in projects:
        projectDir = os.path.join(rootDir, project)
        translationDir = os.path.join(projectDir, 'translations')
        validateProject(project, translationDir)
       
    info("Validation finished.")
    
    
if __name__ == "__main__":
    main()