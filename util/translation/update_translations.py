#!/bin/python2

import sys
import os
import argparse
from multiprocessing import Process
import threading
import subprocess

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getTranslatableProjects
sys.path.pop(0)

buildVarDir = os.path.join(os.getcwd(), 'build_variables/target')
sys.path.insert(0, buildVarDir)
from current_config import QT_DIR
sys.path.pop(0)

ignored = [
            # QT files
            '/qstringbuilder.h', '/qstring.h', '/qmatrix.h', '/qaction.h', '/qnetworkcookiejar.h', '/qboxlayout.h', '/qgridlayout.h',

            # 3rd-party libraries
            '/boost', '/libavutil', '/openssl', '/directx', '/festival',

            # Project files
            '.prf', '.pro(1)', 'Project MESSAGE:'
          ]

errors = [
            # Module lacks Q_OBJECT macro
            'lacks'
         ]

warnings = [
            # Discarding unconsumed metadata, usually warned on sequences like /*=
            'Discarding',

            # Circular inclusions
            'circular'
           ]

verbose = False
results = dict()

def calculateEntries(prefix, dir):
    entries = []

    for entry in os.listdir(dir):
        path = os.path.join(dir, entry)

        if (os.path.isdir(path)):
            continue

        if (not path[-3:] == '.ts'):
            continue

        if (not entry.startswith(prefix)):
            continue

        entries.append(path)
    return entries

def update(project):
    rootDir = os.getcwd()
    projectDir = os.path.join(rootDir, project.path)
    translationDir = os.path.join(projectDir, 'translations')
    sourcesDir = os.path.join(projectDir, project.sources)
    filename = project.name
    
    entries = calculateEntries(filename, translationDir)
    
    lupdate = os.path.join(QT_DIR, 'bin', 'lupdate.exe')
    command = [lupdate, '-no-obsolete', '-no-ui-lines']
  
    command.append('-locations')
    command.append(project.locations)
    command.append('-extensions')
    command.append(project.extensions)
    command.append(sourcesDir)
    command.append('-ts')
    for path in entries:
        command.append(path)
    
    log = ''
    global verbose
    if verbose:
        log += ' '.join(command)
        log += '\n'
    
    log += subprocess.check_output(command, stderr=subprocess.STDOUT)
    global results
    results[project] = log

def handleOutput(log):
    for line in log.split('\n'):
        if len(line) == 0:
            continue

        if any(s in line for s in ignored):
            continue

        if any(s in line for s in warnings):
            warn(line)
            continue

        if any(s in line for s in errors):
            err(line)
            continue

        if verbose:
            info(line)

def updateThreaded(project, callback):
    thread = threading.Thread(None, callback, args=(project,))
    thread.start()
    return thread

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    projects = getTranslatableProjects()   
    threads = []
    for project in projects:
        if verbose:
            info("Updating project " + str(project))           
        threads.append(updateThreaded(project, update))
            
    for thread in threads:
        thread.join()

    for project in projects:
        if verbose:
            separator()
        handleOutput(results[project])


if __name__ == "__main__":
    main()
