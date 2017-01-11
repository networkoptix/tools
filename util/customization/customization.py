#!/bin/python2
# -*- coding: utf-8 -*-

import os

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

'''
Customization class is just a set of icons, collected from several folders.
'''
class Customization():

    '''
        name - customization name (e.g. default or vista)
        root - path to customization folder (./customization/vista)
        project - CustomizableProject instance
    '''
    def __init__(self, name, root, project):
        self.name = name
        self.root = root
        self.project = project
        self.supported = True
        self.parent = None
        self.icons = set()
        self.static_files = project.static_files
        self.cusomized_files = project.cusomized_files
        self.duplicates = set()

        with open(os.path.join(self.root, 'build.properties'), "r") as buildFile:
            for line in buildFile.readlines():
                if 'supported' in line:
                    self.supported = not (line.split('=')[1].strip().lower() == "false")
                if 'parent.customization' in line:
                    self.parent = line.split('=')[1].strip()
                    
        if self.static_files:
            for path in self.static_files:
                self.populateFrom(path)
                
        if self.cusomized_files:
            for path in self.cusomized_files:
                self.populateFrom(os.path.join(self.root, path))

    def __str__(self):
        return self.name

    def isRoot(self):
        if not self.parent:
            err('Invalid build.properties file: ' + os.path.join(self.path, 'build.properties'))
            return False
        return self.parent == self.name

    def populateFrom(self, path):
        for dirname, dirnames, filenames in os.walk(path):
            cut = len(path) + 1
            for filename in filenames:
                if filename[0] == '.':
                    continue;
                key = os.path.join(dirname, filename)[cut:].replace("\\", "/")
                if key in self.icons:
                    self.duplicates.add(key)
                else:
                    self.icons.add(key)
        
    def relativePath(self, path, entry):
        return os.path.relpath(os.path.join(path, entry), self.rootPath)


    def isUnused(self, entry, requiredFiles):
        if not requiredFiles:
            return False
        if '@2x' in entry:
            return False
        if Suffixes.baseName(entry) in requiredFiles:
           return False
        if entry in Project.INTRO:
           return False
        if not Formats.isImage(entry):
           return False
        return True
