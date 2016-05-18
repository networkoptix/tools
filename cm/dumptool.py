#!/usr/bin/python
'''Automatic windows dump analyser tool

Generates test report (cdb-bt) based on dump (dmp). Binaries and debug
information gets automatically from jenkins. Takes about a minute to analyse
(several more if debug information is required).

Dependencies:
    msiexec - standart windows tool (comes with windows)
    7x - zip extracter (comes with buildenv/_setenv.bat)
    cdb - windows debugger (comes with Windows SDK)

Usage (module):
    > import dumptool
    > print dumptool.analyseDump('dump.dmp', customization)
    dump.cdb-bt

Usage (console):
    > python dumptool.py dump.dmp [customization]
    dump.cdb-bt
'''

import os
import re
import string
import subprocess
import sys
import urllib2

CONFIG = dict(
    cdb_path = 'cdb',
    data_dir = 'c:/develop/dumptool/',
    dist_url = 'http://beta.networkoptix.com/beta-builds/daily/',
    ext = dict(
        dump = 'dmp',
        report = 'cdb-bt',
    ),
    msi_suffix = 'x64-%s-only.msi',
    pdb_suffixes = [
        'x64-windows-pdb-all.zip',
        'x64-windows-pdb-apps.zip',
    ],
)

class Error(Exception):
    pass

class Cdb(object):
    '''Cdb programm driver to analize DMP files
    '''

    def __init__(self, dump, debug=None):
        '''Starts up cdb with :dump and :debug path
        '''
        cmd = [CONFIG['cdb_path'], '-z', dump]
        if debug: cmd += ['-i', debug]
        try:
            self.cdb = subprocess.Popen(cmd,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError as e:
            raise Error('Cannot start %s - %s' % (cmd, e))
        self.execute()
        if debug: self.execute('.reload /f')

    def __enter__(self, *a):
        return self

    def __exit__(self, *a):
        try: self.cdb.communicate('q\n')
        except: pass

    def execute(self, command = None):
        '''Executes cdb :command and returns collected output
        '''
        if command:
            self.cdb.stdin.write('%s\n' % command)
        out = ''
        while not out.endswith('\n0:'):
            out += self.cdb.stdout.read(1)
        while self.cdb.stdout.read(1) != '>': # read prompt
            pass
        return out[1:-3] # cut of prompt

    def main_module(self):
        '''Finds executable name (without extension)
        '''
        return self.execute('|').split('\n')[-1].split('\\')[-1][:-4]

    def module_info(self, module, key):
        '''Returns key-value information about :module
        '''
        name = module.translate(string.maketrans(' .', '__'))
        for line in self.execute('lmvm%s\n' % name).split('\n'):
            if line.find(key) != -1:
                return line.split(':')[1].strip()
        raise Error("Attribute '%s' is not found" % key)

    def report(self):
        '''Generates text crash report (cdb-bt)
        '''
        return '\n\n'.join([
            self.execute('.exr -1'), # Error
            self.execute('.ecxr'), # context
            self.execute('kc'), # Error stack
            self.execute('~*kc'), # all threads stacks
        ])

class DumpAnalyzer(object):
    '''Provides ability to analize windows DMP dumps
    '''

    def __init__(
        self, path, customization='default',
        version=None, build=None, verbose=0):
        '''Initializes analizer with dump :path and :customization
        '''
        self.dump_path = path
        self.customization = customization
        self.version = version
        self.build = build
        self.verbose = verbose

    def log(self, message, level=0):
        '''Logs data in case of verbose mode
        '''
        if level < int(self.verbose):
            sys.stderr.write('> %s\n' % message)

    def get_dump_information(self):
        '''Gets initial information from dump
        '''
        with Cdb(self.dump_path) as cdb:
            self.module = cdb.main_module()
            self.version = self.version or cdb.module_info(self.module, 'version')
        if self.module.find('server') != -1:
            self.msi = CONFIG['msi_suffix'] % 'server'
        else:
            self.msi = CONFIG['msi_suffix'] % 'client'
        self.log('Dump information: %s (%s) %s %s ' % (
            self.module, self.msi, self.version, self.customization))
        self.build = self.build or self.version.split('.')[-1]
        if self.build == '0':
            raise Error('Build 0 is not supported')

    def fetch_url_data(self, url, regexps):
        '''Fetches data from :url by :regexp (must contain single group!)
        '''
        try:
            page = urllib2.urlopen(url).read().replace('\n', '')
        except urllib2.HTTPError as e:
            raise Error('%s, url: %s' % (e, url))
        result = []
        for regexp in regexps:
            m = re.match('.+%s.+' % regexp, page)
            if m: result.append(m.group(1))
            else: self.log("Warning: canot find '%s' in %s" % (regexp, url))
        return result

    def fetch_urls(self):
        '''Fetches URLs of required resourses
        '''
        out = self.fetch_url_data(
            CONFIG['dist_url'], ['''(%s\-[^/]+)''' % self.build])
        build_path = '%s/%s/windows/' % (out[0], self.customization)
        build_url = os.path.join(CONFIG['dist_url'], build_path)
        out = self.fetch_url_data(
            build_url, ('''\"(.+\-%s)\"''' % r for r in [
                self.msi] + CONFIG['pdb_suffixes']))
        self.dist_urls = list(os.path.join(build_url, e) for e in out)
        self.build_path = os.path.join(CONFIG['data_dir'], build_path)
        self.target_path = os.path.join(self.build_path, 'target')
        if not os.path.isdir(self.target_path):
            os.makedirs(self.target_path)

    @staticmethod
    def download_url_data(url, local, processor = lambda path: None):
        '''Downloads file from :url to :local directory, apply :processor if any
        '''
        file = os.path.join(local, os.path.basename(url))
        if not os.path.isfile(file):
            with open(file, 'wb') as f:
                f.write(urllib2.urlopen(url).read())
            processor(file)

    def find_file(self, name):
        '''Searches file :name in build directory
        '''
        for root, dirs, files in os.walk(self.build_path):
            if name in files:
                return os.path.join(root, name)
        raise Error("No such file '%s' in '%s'" % (name, path))

    def extract_dist(self, path):
        '''Extract distributive by :path based in it's format
        '''
        def run(*cmd):
            try:
                return subprocess.check_output(cmd)
            except IOError as e:
                raise Error('Cannot run %s - %s' % (cmd, e))
        if path.endswith('.msi'):
            return run(
                'msiexec', '-a', path.replace('/', '\\'),
                '/qb', 'TARGETDIR=' + self.target_path.replace('/', '\\'))
        if path.endswith('.zip'):
            self.module_dir = os.path.dirname(
                self.find_file(self.module + '.exe'))
            return run(
                '7z', 'x', path, '-o' + self.module_dir, '-y')

    def download_dists(self):
        '''Downloads required distributives
        '''
        for url in self.dist_urls:
            self.log('Download: ' + url)
            self.download_url_data(url, self.build_path, self.extract_dist)
        self.module_dir = os.path.dirname(self.find_file(self.module + '.exe'))

    def report_name(self):
        '''Generates report name based on dump name
        '''
        dump_ext = '.' + CONFIG['ext']['dump']
        if not self.dump_path.lower().endswith(dump_ext):
            raise Error('Only *%s dumps are supported' % dump_ext)
        report_ext = '.' + CONFIG['ext']['report']
        return self.dump_path[:-len(dump_ext)] + report_ext


    def generate_report(self):
        '''Generates report using cdb with debug information
        '''
        report_path = self.report_name()
        self.log('Loading debug information: ' + self.module_dir)
        with Cdb(self.dump_path, debug=self.module_dir) as cdb:
            self.log('Generating report: ' + report_path)
            with open(report_path, 'w') as report:
                report.write(cdb.report())
        return report_path

def analyseDump(*args, **kwargs):
    '''Generated cdb-bt report based on dmp file
    Note: Returns right away in case if dump is already analized
    Returns: cdb-bt report path
    '''
    dump = DumpAnalyzer(*args, **kwargs)
    report = dump.report_name()
    if os.path.isfile(report):
        dump.log('Already processed: ' + report)
        return report
    dump.get_dump_information()
    dump.fetch_urls()
    dump.download_dists()
    return dump.generate_report()

def main():
    args, kwargs = list(), dict()
    for arg in sys.argv[1:]:
        s = arg.split('=', 2)
        if len(s) == 1: args.append(s[0])
        else: kwargs[s[0]] = s[1]
    try:
        print analyseDump(*args, **kwargs)
    except Error as e:
        sys.stderr.write('Error: %s\n' % e)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stderr.write('Interrupted\n')

if __name__ == '__main__':
    main()

