#/bin/python

import sys
import os
import argparse

projects = ['common', 'client', 'traytool']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--language', help="target language", required=True)
    args = parser.parse_args()
    language = args.language

    rootDir = os.getcwd()
    
    for project in projects:
        projectDir = os.path.join(rootDir, project)
        translationDir = os.path.join(projectDir, 'translations')
        template = os.path.join(translationDir, 'template.xml')
        target = os.path.join(translationDir, project + '_' + language + '.ts')
        
        with open(template, "r") as src, open(target, "w") as tgt:
            for line in src:
                tgt.write(line.replace('%', language))
    print "ok"
    
    
if __name__ == "__main__":
    main()
