#/usr/bin/python2
# -*- coding: utf-8 -*-
""" Runs through netoptix_vms directories tree and check
if all pom.xml files have the same <version>.
(excluding common_libs/udt project that may have another version, but must have correct parent version).
Issue: https://networkoptix.atlassian.net/browse/ENV-57
"""

import os
import sys
import argparse
import re
import xml.etree.ElementTree as ET
import traceback
from common_module import init_color,info,green,warn,err

pomFileName = "pom.xml"
rootDir = os.getcwd() # TODO make it possible to use the parameter
verbose = False

parentOnlyCheck = [] # use any subpaths here (example: 'common_libs/udt') 
                     # to check only parent version there (not recurcive in subdirs)

def strip_root(filename):
    if filename.startswith(rootDir):
        return filename[len(rootDir):].lstrip('/')
    return filename


def subgetVersion(element, ns, file):
    version = None
    for v in element.findall('{0}version'.format(ns)):
        if version is None:
            version = v.text
        else:
            err("Too many <version>s found in <{0}> in {1}".format(element.tag, file))
    return version


def getVersionsXML(fileName):
    parent_version = None
    version = ''
    try:
        tree = ET.parse(fileName)
        # extract the default namespace, the root element of pom.xml should be 'project' from this namespace
        root = tree.getroot()
        m = re.match("(\{[^}]+\}).+", root.tag)
        # unfortunately, xml.etree.ElementTree adds namespace to all tags and there is no way to use clear tag names
        ns = m.group(1) if m else ''
        shortFn = strip_root(fileName)
        version = subgetVersion(root, ns, shortFn)
        for p in root.findall('{0}parent'.format(ns)):
            if parent_version is None:
                parent_version = ''
            v = subgetVersion(p, ns, shortFn)
            if parent_version:
                err("Too many <parents>s found in {0}".format(shortFn))
            else:
                parent_version = v
    except Exception:
        err("Error parsing XML in %s:\n%s" % (fileName, traceback.format_exc()))
    return version, parent_version


def checkVersion(root_version, filename, parentOnly):
    ok = True
    version, parent = getVersionsXML(filename)
    if not parentOnly and version != root_version:
        ok = False
        if version:
            err("{0} has version {1}".format(strip_root(filename), version))
        else:
            err("{0} has no version".format(strip_root(filename)))
    if parent != root_version:
        ok = False
        if parent:
            err("{0} has parent version {1}".format(strip_root(filename), parent))
        elif parent is None:
            err("{0} has NO <parent> at all".format(strip_root(filename)))
        else:
            err("{0} has NO parent version".format(strip_root(filename)))
    if verbose and ok:
        info("{0} - OK".format(strip_root(filename)))


def checkVersionRecursive():
    version, _ = getVersionsXML(os.path.join(rootDir, pomFileName))
    if not version:
        err('The version cannot be detected')
        sys.exit(1)

    info('The root {0} file version is {1}'.format(pomFileName, version))

    for path, subdirs, files in os.walk(rootDir):
        try:
            subdirs.remove('.hg')
        except ValueError:
            pass
        if path != rootDir and pomFileName in files:
            checkVersion(version, os.path.join(path, pomFileName), strip_root(path) in parentOnlyCheck)


def main():      
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="more messages")
    args = parser.parse_args()

    if args.color:
        init_color()
    if args.verbose:
        global verbose
        verbose = True
    
    checkVersionRecursive()


if __name__ == "__main__":
    main()
