#!/bin/python2

import sys
import os
import argparse
import threading
import subprocess

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'util')
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

ignored = [
    # QT files
    '/qstringbuilder.h',
    '/qstring.h',
    '/qmatrix.h',
    '/qaction.h',
    '/qnetworkcookiejar.h',
    '/qboxlayout.h',
    '/qgridlayout.h',

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
lupdate = None


def isBinary(binary):
    return any(os.access(os.path.join(path, binary), os.X_OK) for path in os.environ["PATH"].split(os.pathsep))


def detectLUpdate():
    global lupdate
    if isBinary('lupdate'):
        lupdate = 'lupdate'
    elif isBinary('lupdate.exe'):
        lupdate = 'lupdate.exe'
    elif os.path.isfile('current_config.py'):
        sys.path.insert(0, os.getcwd())
        from current_config import QT_DIR, PROJECT_SOURCE_DIR
        lupdate = os.path.join(QT_DIR, 'bin', 'lupdate.exe')
        os.chdir(PROJECT_SOURCE_DIR)
        sys.path.pop(0)
    else:
        buildVarDir = os.path.join(os.getcwd(), 'build_variables/target')
        sys.path.insert(0, buildVarDir)
        if os.path.isfile('current_config.py'):
            from current_config import QT_DIR
            lupdate = os.path.join(QT_DIR, 'bin', 'lupdate.exe')
        sys.path.pop(0)


def calculateEntries(prefix, dir, language):
    entries = []
    suffix = language + '.ts'

    for entry in os.listdir(dir):
        path = os.path.join(dir, entry)

        if (os.path.isdir(path)):
            continue

        if not path.endswith(suffix):
            continue

        if not entry.startswith(prefix):
            continue

        entries.append(path)

    if len(entries) == 0:
        err("No {}*{} files were found in {}".format(prefix, suffix, dir))
    return entries


def update(project, language):
    rootDir = os.getcwd()
    projectDir = os.path.join(rootDir, project.path)
    translationDir = os.path.join(projectDir, 'translations')
    sourcesDir = os.path.join(projectDir, project.sources)
    filename = project.name

    entries = calculateEntries(filename, translationDir, language)

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


def updateThreaded(project, language, callback):
    thread = threading.Thread(None, callback, args=(project, language))
    thread.start()
    return thread


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-l', '--language', default="en_US")
    parser.add_argument('-p', '--project')
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    if args.color:
        init_color()

    detectLUpdate()
    if not lupdate:
        err('lupdate is not found in PATH')
        return 1
    info('Using {0}'.format(lupdate))

    projectDir = os.path.join(os.getcwd(), 'build_utils/validation')
    sys.path.insert(0, projectDir)
    from translatable_projects import get_translatable_projects
    sys.path.pop(0)

    projects = list(get_translatable_projects(args.project))
    if not projects:
        err("Projects list could not be read")
    threads = []
    for project in projects:
        if verbose:
            info("Updating project " + str(project))
        threads.append(updateThreaded(project, args.language, update))

    if verbose:
        info("Waiting for {} threads".format(len(threads)))
    for thread in threads:
        thread.join()
    if verbose:
        info("{} projects processed".format(len(projects)))

    for project in projects:
        if verbose:
            separator()
        handleOutput(results[project])


if __name__ == "__main__":
    main()
