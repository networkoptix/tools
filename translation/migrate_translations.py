# -*- coding: utf-8 -*-
#/bin/python

import sys
import os
import argparse
import difflib
import xml.etree.ElementTree as ET
from common_module import init_color,info,green,warn,err,separator

projects = ['common', 'client', 'traytool']
verbose = False
similarityLevel = 100
    
ignored = ['Ctrl+', 'Shift+', 'Alt+']
    
class MigrationResult():
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
        
        if (os.path.isdir(path)):
            continue;
                
        if (not path[-2:] == 'ts'):
            continue;
            
        if (not entry.startswith(project)):
            continue;
            
        if 'en_US' in entry:
            continue
                
        sourcePath = os.path.join(sourceTranslationDir, entry)
        if (not os.path.isfile):
            err("{0} not found in the source dir {1}".format(entry, sourceTranslationDir))
            continue
            
        entries[path] = sourcePath
            
    for path, sourcePath in entries.items():
        migrateFile(path, sourcePath)

def main():
    parser = argparse.ArgumentParser()
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
    
    for project in projects:
        projectDir = os.path.join(rootDir, project)
        sourceProjectDir = os.path.join(args.source, project)
        
        translationDir = os.path.join(projectDir, 'translations')
        sourceTranslationDir = os.path.join(sourceProjectDir, 'translations')
        
        migrateProject(project, translationDir, sourceTranslationDir)
       
    if verbose:
        info("Migration finished.")
    
    
if __name__ == "__main__":
    main()