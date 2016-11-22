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
    msi_suffix = 'x64[a-z\-]+%s-only.msi',
    pdb_suffixes = [
        'x64[a-z\\-]+windows-pdb-all.zip',
        'x64[a-z\\-]+windows-pdb-apps.zip',
    ],
)

CONFIG['7z_path'] = 'C:\\Program Files\\7-Zip\\7z.exe'
CONFIG['cdb_path'] = 'C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\cdb.exe'

class Error(Exception):
    pass


def report_name(dump_path, safe=False):
    '''Generates report name based on dump name
    '''
    dump_ext = '.' + CONFIG['ext']['dump']
    if not dump_path.lower().endswith(dump_ext):
        if safe:
            return ''  # to calls where exceptions aren't wanted
        raise Error('Only *%s dumps are supported' % dump_ext)
    report_ext = '.' + CONFIG['ext']['report']
    return dump_path[:-len(dump_ext)] + report_ext


def clear_cache(cacheDir, keepFiles):
    print "Clearing cache dir %s" % (cacheDir,)
    existing = set(os.listdir(cacheDir))
    for fname in keepFiles:
        existing.discard(report_name(fname, True))
    # remove all files not mentioned in keepFiles
    for fname in existing:
        try:
            os.remove(os.path.join(cacheDir, fname))
        except IOError:
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
        if debug:
            self.execute('.sympath+ "%s"' % debug)
            self.execute('.reload /f')

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
        def read_ch():
            c = self.cdb.stdout.read(1)
            if not c: raise Error(
                "Cdb command: %s\nUnexpected eof: %s" % (command, out))
            return c
        while not out.endswith('\n0:'): out += read_ch()
        while self.cdb.stdout.read(1) != '>': pass
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
            self.log("DEBUG: CDB reports main module: " + self.module)
            self.version = self.version or cdb.module_info(self.module, 'version')
            self.log("DEBUG: CDB reports version: " + self.version)
        self.msi = 'server' if self.module.find('server') != -1 else 'client'
        self.log('Dump information: %s (%s) %s %s ' % (
            self.module, self.msi, self.version, self.customization))
        self.build = self.build or self.version.split('.')[-1]
        if self.build == '0':
            raise Error('Build 0 is not supported')

    def fetch_url_data(self, url, regexps, subUrl=None):
        '''Fetches data from :url by :regexp (must contain single group!)
        '''
        try:
            page = urllib2.urlopen(url).read().replace('\n', '')
        except urllib2.HTTPError as e:
            raise Error('%s, url: %s' % (e, url))
        #print "DEBUG (PAGE): %s" % (page,)
        results, failures = [], []
        for regexp in regexps:
            rx = '.+%s.+' % regexp
            self.log("Trying regexp /%s/" % (rx,), level=1)
            m = re.match(rx, page)
            if m:
		print "DEBUG: regexp /%s/ got url '%s'" % (rx, m.group(1))
                results.append((url, m.group(1)))
            else:
                failures.append(regexp)
                self.log("Warning: canot find '%s' in %s" % (regexp, url))
        if subUrl and len(failures):
            results += self.fetch_url_data(subUrl, failures)
        return results

    def fetch_urls(self):
        '''Fetches URLs of required resourses
        '''
        out = self.fetch_url_data(
            CONFIG['dist_url'], ['''href="(%s\-[^/]+)"''' % self.build])
        if len(out) == 0:
            print "No distributive found for build %s. Dump analyze imposible" % self.build
            return False
        build_path = '%s/%s/windows/' % (out[0][1], self.customization)
        update_path = '%s/%s/updates/%s/' % (out[0][1], self.customization, self.build)
        build_url = os.path.join(CONFIG['dist_url'], build_path)
        print "DEBUG: build_url = '%s',\ndist_url = '%s'\nbuild_path = '%s'" % (
              build_url, CONFIG['dist_url'], build_path)
        out = self.fetch_url_data(
            build_url, ('''\"(.+\-%s)\"''' % r for r in [
                CONFIG['msi_suffix'] % self.msi] + CONFIG['pdb_suffixes']),
            os.path.join(CONFIG['dist_url'], update_path))
        self.dist_urls = list(os.path.join(*e) for e in out)
        self.build_path = os.path.join(CONFIG['data_dir'],  build_path)
        self.target_path = os.path.join(self.build_path, 'target')
        if not os.path.isdir(self.target_path):
            os.makedirs(self.target_path)
        return True

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
        raise Error("No such file '%s' in '%s'" % (name, self.build_path))

    def extract_dist(self, path):
        '''Extract distributive by :path based in it's format
        '''
        self.log("Extracting %s ..." % (path,))
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
                CONFIG['7z_path'], 'x', path, '-o' + self.module_dir, '-y')

    def download_dists(self):
        '''Downloads required distributives
        '''
        if not self.dist_urls:
           raise Error('There are no any dist URLs avaliable')
        for url in self.dist_urls:
            self.log('Download: %s to %s' % (url, self.build_path))
            self.download_url_data(url, self.build_path, self.extract_dist)
        self.module_dir = os.path.dirname(self.find_file(self.module + '.exe'))

    def generate_report(self, asString=False):
        '''Generates report using cdb with debug information
        '''
        report_path = report_name(self.dump_path)
        self.log('Loading debug information: ' + self.module_dir)
        with Cdb(self.dump_path, debug=self.module_dir) as cdb:
            self.log('Generating report: ' + report_path)
            report = cdb.report()
            with open(report_path, 'w') as report_file:
                report_file.write(report)
        return report if asString else report_path


FORMATS = {'path', 'str', 'dict'}

def _resultDict(dump, text):
    return dict(
        component = dump.msi,
        dump = text
    )

def analyseDump(*args, **kwargs):
    '''Generated cdb-bt report based on dmp file
    Note: Returns right away in case if dump is already analized
    Returns: cdb-bt report path
    '''
    format = kwargs.pop('format', 'path')  # possible values: path, str, dict
    if not format in FORMATS:
        raise Error("Wrong format value: %s" % format)
    dump = DumpAnalyzer(*args, **kwargs)
    report = report_name(dump.dump_path)
    if os.path.isfile(report):
        if format == 'dict':
            dump.get_dump_information()
            return _resultDict(dump, open(report, 'r').read())
        elif format == 'str':
            return open(report, 'r').read()
        else:
            dump.log('Already processed: ' + report)
            return report
    dump.get_dump_information()
    if not dump.fetch_urls():
        return dict() if format == 'dict' else ''
    dump.download_dists()
    reportText = dump.generate_report(format != 'path')
    return _resultDict(dump, reportText) if format == 'dict' else reportText

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
#    except KeyboardInterrupt:
#        sys.stderr.write('Interrupted\n')

if __name__ == '__main__':
    main()

