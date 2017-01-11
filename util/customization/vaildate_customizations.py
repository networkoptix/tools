#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import argparse
import os
from itertools import combinations
from customization import Customization

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

projectDir = os.path.join(os.getcwd(), 'build_utils/python')
sys.path.insert(0, projectDir)
from vms_projects import getCustomizableProjects
sys.path.pop(0)


class Intro:
    CLIENT = "client"
    FILES = {"intro.mkv", "intro.avi", "intro.png", "intro.jpg", "intro.jpeg"}

    @staticmethod
    def validate(customization):
        if customization.project.name == Intro.CLIENT:
            return len(customization.icons & Intro.FILES) == 1
        return True

class Formats:
    PNG = '.png'
    GIF = '.gif'
    IMAGES = [PNG, GIF]
    AI = '.ai'
    SVG = '.svg'

    CPP = '.cpp'
    H   = '.h'
    UI  = '.ui'
    SOURCES = [CPP, H, UI]

    @staticmethod
    def isImage(string):
        if '%' in string:
            return False
        if '*' in string:
            return False
        for format in Formats.IMAGES:
            if format in string and string != format:
                return True
        return False

    @staticmethod
    def isSource(string):
        for format in Formats.SOURCES:
            if string.endswith(format):
                return True
        return False

verbose = False

def validateCustomization(customization):
    info('Customization: ' + customization.name)
    for duplicate in customization.duplicates:
        err("Duplicate file {0}".format(duplicate))

    if not Intro.validate(customization):
        err("Intro is not found")

def crossCheckCustomizations(first, second):
    info('Compare: ' + first.name + ' vs ' + second.name)

def parseLine(line, extension, location):
    global verbose
    result = []
    splitter = '"'
    if extension == Formats.UI:
        line = line.replace("<", splitter).replace(">", splitter).replace(":/skin/", "")

    for part in line.split(splitter):
        if not Formats.isImage(part):
            continue
        result.append(part)
    return result

def parseFile(path):
    global verbose
    result = []
    linenumber = 0
    extension = os.path.splitext(path)[1]
    with open(path, "r") as file:
        for line in file.readlines():
            linenumber += 1
            if not Formats.isImage(line):
                continue
            result.extend(parseLine(line, extension, "%s:%s" % (path, linenumber)))
    return result

def parseSources(dir):
    result = []
    if not os.path.exists(dir):
        return result
    for entry in os.listdir(dir):
        path = os.path.join(dir, entry)
        if (os.path.isdir(path)):
            result.extend(parseSources(path))
            continue
        if not Formats.isSource(path):
            continue
        result.extend(parseFile(path))
    return result

def textCell(file, text, style = None):
    if style:
        file.write('\t<td class="%s">' % (style))
    else:
        file.write("\t<td>")
    file.write(text)
    file.write("</td>\n")

def imgCell(file, text, style):
    file.write('\t<td class="%s"><img src="%s"/></td>\n' % (style, text))

def printCustomizations(project, customizationDir, requiredFiles, customizations, roots, children):
    filename = os.path.join(customizationDir, project + ".html")
    file = open(filename, 'w')

    file.write("""<style>
img {max-width: 64px; }
td { text-align: center; }
td.label { text-align: left; }
td.dark { background-color: #222222; }
td.light { background-color: #D0D0D0; }
</style>\n""")
    file.write("<table>\n")
    file.write("<tr>\n")
    file.write("<th>File</th>\n")
    for c in roots:
        file.write("<th colspan=2>%s</th>\n" % c.name)
    for c in children:
        file.write("<th colspan=2>%s</th>\n" % c.name)
    file.write("</tr>\n")

    for entry in requiredFiles:
        if not Formats.isImage(entry):
            continue;
        file.write("<tr>\n")
        textCell(file, entry, "label")
        for c in roots:
            if entry in c.dark:
                imgCell(file, os.path.relpath(os.path.join(c.darkPath, entry), customizationDir), "dark")
            elif entry in c.base:
                imgCell(file, os.path.relpath(os.path.join(c.basePath, entry), customizationDir), "dark")
            else:
                textCell(file, "-")

            if entry in c.light:
                imgCell(file, os.path.relpath(os.path.join(c.lightPath, entry), customizationDir), "light")
            elif entry in c.base:
                imgCell(file, os.path.relpath(os.path.join(c.basePath, entry), customizationDir), "light")
            else:
                textCell(file, "-")

        for c in children:
            p = customizations[c.parent]
            if entry in c.dark:
                imgCell(file, os.path.relpath(os.path.join(c.darkPath, entry), customizationDir), "dark")
            elif entry in c.base:
                imgCell(file, os.path.relpath(os.path.join(c.basePath, entry), customizationDir), "dark")
            elif entry in p.dark:
                imgCell(file, os.path.relpath(os.path.join(p.darkPath, entry), customizationDir), "dark")
            elif entry in p.base:
                imgCell(file, os.path.relpath(os.path.join(p.basePath, entry), customizationDir), "dark")
            else:
                textCell(file, "-")

            if entry in c.light:
                imgCell(file, os.path.relpath(os.path.join(c.lightPath, entry), customizationDir), "light")
            elif entry in c.base:
                imgCell(file, os.path.relpath(os.path.join(c.basePath, entry), customizationDir), "light")
            elif entry in p.light:
                imgCell(file, os.path.relpath(os.path.join(p.lightPath, entry), customizationDir), "light")
            elif entry in p.base:
                imgCell(file, os.path.relpath(os.path.join(p.basePath, entry), customizationDir), "light")
            else:
                textCell(file, "-")

        file.write("</tr>\n")

    file.write("</table>")
    file.truncate()
    file.close()

def checkProject(rootDir, project):
    separator()
    info("Validating project " + project.name)
    roots = []

    if project.sources:
        requiredFiles = []
        for srcDir in project.sources:
            sourcesDir = os.path.join(rootDir, srcDir)
            requiredFiles += parseSources(sourcesDir)
        requiredSorted = sorted(list(set(requiredFiles)))
    else:
        requiredSorted = None

    customizationDir = os.path.join(rootDir, "customization")

    for entry in os.listdir(customizationDir):
        if (entry[:1] == '_'):
            continue
        path = os.path.join(customizationDir, entry)
        if (not os.path.isdir(path)):
            continue
        c = Customization(entry, path, project)
        if not c.supported:
            info('Skip unsupported customization {0}'.format(c.name))
            continue
            
        validateCustomization(c)
        if c.isRoot():
            roots.append(c)

    for c1, c2 in combinations(roots, 2):
        crossCheckCustomizations(c1, c2)
        crossCheckCustomizations(c2, c1)
    info('Validation finished')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    args = parser.parse_args()
    if args.color:
        init_color()

    global verbose
    verbose = args.verbose

    rootDir = os.getcwd()
    projects = getCustomizableProjects()

    for project in projects:
        checkProject(rootDir, project)

if __name__ == "__main__":
    main()
    sys.exit(0)