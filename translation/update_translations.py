#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import os
import argparse
from multiprocessing import Process
import threading
import subprocess
from common_module import init_color,info,green,warn,err,separator

projects = {
    'common': [],
    'traytool': [],
    'client': ['base', 'ui'],
    'mobile_client': ['base', 'qml']
}

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

def update(project, suffix = '', filter = ' -locations none'):
    rootDir = os.getcwd()
    projectDir = os.path.join(rootDir, project)
    translationDir = os.path.join(projectDir, 'translations')
    if suffix == 'qml':
        sourcesDir = os.path.join(projectDir, 'static-resources')
    else:
        sourcesDir = os.path.join(projectDir, 'src')

    filename = project
    if suffix:
        filename += '_'
        filename += suffix
    entries = calculateEntries(filename, translationDir)

    command = 'c:\\develop\\buildenv\\qt5\\qtbase-x64\\bin\\lupdate.exe -no-obsolete -no-ui-lines'
    if filter:
        command += filter
    command += ' ' + sourcesDir
    command += ' -ts'
    for path in entries:
        command = command + ' ' + path
    log = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    global results
    results[project] = log

def updateBase(project):
    update(project, 'base',  ' -extensions cpp,h  -locations none')

def updateUi(project):
    update(project, 'ui',  ' -extensions ui -locations relative')

def updateQml(project):
    update(project, 'qml',  ' -extensions qml -locations none')

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

    threads = []
    for project, targets in projects.items():
        if not targets:
            if verbose:
                info("Updating default project " + project)
            threads.append(updateThreaded(project, update))
        else:
            for target in targets:
                info("Updating {0} project ".format(target) + project)

                if target == 'base':
                    threads.append(updateThreaded(project, updateBase))
                elif target == 'ui':
                    threads.append(updateThreaded(project, updateUi))
                elif target == 'qml':
                    threads.append(updateThreaded(project, updateQml))

    for thread in threads:
        thread.join()

    for project in projects:
        separator()
        handleOutput(results[project])


if __name__ == "__main__":
    main()
