# -*- coding: utf-8 -*-
#/bin/python

import sys
import os
import argparse
from multiprocessing import Process
import threading
import subprocess
from common_module import init_color,info,green,warn,err,separator

projects = ['common', 'traytool', 'client']
ignored = [
            'qstringbuilder.h', 'qstring.h', 'qmatrix.h', 'qaction.h', 'qnetworkcookiejar.h',
            '/boost', '/libavutil', '/openssl', 
            '.prf', '.pro(1)'
          ]
verbose = False
results = dict()

def update(project, translationDir, projectFile):
    entries = []

    for entry in os.listdir(translationDir):
        path = os.path.join(translationDir, entry)
        
        if (os.path.isdir(path)):
            continue
                
        if (not path[-2:] == 'ts'):
            continue
            
        if (not entry.startswith(project)):
            continue
            
        entries.append(path)
            
    command = 'lupdate -no-obsolete -no-ui-lines -pro ' + projectFile + ' -locations none -ts'
    for path in entries:
        command = command + ' ' + path
    if verbose:
        info(command)
        separator()
    log = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    global results
    results[project] = log

def handleOutput(log):
    for line in log.split('\n'):
        line = line.strip('\n')
        if len(line) == 0:
            continue;
        
        skipLine = False
        for s in ignored:
            if s in line:
                skipLine = True
        if skipLine:
            continue;
                
        if "Discarding" in line:
            warn(line)
        elif "lacks" in line:
            err(line)
        elif verbose:
            info(line)
            
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
    
    threads = []
    for project in projects:
        projectDir = os.path.join(rootDir, project)
        translationDir = os.path.join(projectDir, 'translations')
        projectFile = os.path.join(projectDir, 'x64/' + project + '.pro')
        #thread = Process(target=update, args=(project, translationDir, projectFile))
        thread = threading.Thread(None, update, args=(project, translationDir, projectFile))
        thread.start()
        threads.append(thread)
        
    for thread in threads:
        thread.join()
        
    for project in projects:
        separator()
        handleOutput(results[project])
   
    
if __name__ == "__main__":
    main()