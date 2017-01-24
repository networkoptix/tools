import os

from file_formats import is_image_file

suffixes = ['_hovered', '_selected', '_pressed', '_disabled', '_checked', '_accented', '@2x', '@3x', '@4x']

def basename(icon):
    result = icon;
    for suffix in suffixes:
        result = result.replace(suffix, "")
    return result

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
        self.icons = set()
        self.other_files = set()
        self.static_files = project.static_files
        self.customized_files = project.customized_files
        self.duplicates = set()
        self.build_properties = {}

        with open(os.path.join(self.root, 'build.properties'), "r") as buildFile:
            for line in buildFile.readlines():
                if line.startswith('#'):
                    continue
                if line.startswith('['):
                    continue
                key, sep, value = line.partition('=')
                if not key.strip():
                    continue
                self.build_properties[key.strip()] = value.strip()
           
        self.supported = not self.buildProperty('supported') == "false"
        self.parent = self.buildProperty('parent.customization')

        if self.static_files:
            for path in self.static_files:
                self.populateFrom(path)

        if self.customized_files:
            for path in self.customized_files:
                self.populateFrom(os.path.join(self.root, path))

    def buildProperty(self, name, default = None):
        if name in self.build_properties:
            return self.build_properties[name]
        return default
                
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
                if not is_image_file(key):
                    self.other_files.add(key)
                elif key in self.icons:
                    self.duplicates.add(key)
                else:
                    self.icons.add(key)

    def baseIcons(self):        
        for icon in sorted(self.icons):
            yield basename(icon), icon

    def relativePath(self, path, entry):
        return os.path.relpath(os.path.join(path, entry), self.rootPath)
