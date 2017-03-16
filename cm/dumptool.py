#!/usr/bin/python
'''Automatic windows dump analyser tool

Generates test report (cdb-bt) based on dump (dmp). Binaries and debug
information gets automatically from jenkins. Takes about a minute to analyse
(several more if debug information is required).

Dependencies:
    msiexec - standart windows tool (comes with windows)
    7x - zip extracter (comes with buildenv/_setenv.bat)
    cdb - windows debugger (comes with Windows SDK)
    dark - wix extractor (comes with wix toolset: wixtoolset.org)

Usage (module):
    > import dumptool
    > print dumptool.analyseDump('dump.dmp', customization[, branch=BRANCH][, verbose=N])
    dump.cdb-bt

Usage (console):
    $ python dumptool.py dump.dmp [customization] [branch=BRANCH] [verbose=N]
    dump.cdb-bt
'''

import os
import re
import shutil
import string
import subprocess
import sys
import urllib2

CONFIG = dict(
    cdb_path = 'cdb',
    zip_path = '7z',
    data_dir = 'c:/develop/dumptool/',
    dist_url = 'http://beta.networkoptix.com/beta-builds/daily/',
    ext = dict(
        dump = 'dmp',
        report = 'cdb-bt',
    ),
    dist_suffixes = [
        '''x64[a-z-_]+%s(-only)?\.(msi|exe)''',
        '''%s-[0-9\.-_]+-win64[a-z-_]+\.(exe|msi)''',
    ],
    pdb_suffixes = [
        '''x64[a-z-_]+windows-pdb-(all|apps|%(module)s|libs)\.zip''',
        '''(%(module)s|libs)_debug-[0-9\.-_]+-win64[a-z-_]+\.zip''',
    ],
)

#CONFIG['zip_path'] = 'C:\\Program Files\\7-Zip\\7z.exe'
#CONFIG['cdb_path'] = 'C:\\Program Files (x86)\\Windows Kits\\10\\Debuggers\\x64\\cdb.exe'

class Error(Exception):
    '''Base error type.
    '''
    pass

class CdbError(Error):
    '''Cdb driver related error.
    '''
    pass

class UserError(Error):
    '''Invalid usage, e.g. unsupported format or build number.
    '''
    pass

class DistError(Error):
    '''Distribution related errors, e.g. distribution in not found or invalid.
    '''
    pass

def report_name(dump_path, safe=False):
    '''Generates report name based on dump name.
    '''
    dump_ext = '.' + CONFIG['ext']['dump']
    if not dump_path.lower().endswith(dump_ext):
        if safe:
            return ''  # to calls where exceptions aren't wanted
        raise UserError('Only *%s dumps are supported, rejected: %s' % (
            dump_ext, dump_path))
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

def shell_line(command):
    return ' '.join(
        '"%s"' % arg if arg.find(' ') != -1 else arg for arg in command)

class Cdb(object):
    '''Cdb program driver to analize DMP files.
    '''

    def __init__(self, dump, exe_dir=None, pdb_dirs=None):
        '''Starts up cdb with :dump, :exe_dir and :pdb_dir.
        '''
        self.shell = [CONFIG['cdb_path'], '-z', dump]
        if exe_dir:
           self.shell += ['-i', exe_dir]
        if pdb_dirs:
           self.shell += ['-y', 'srv*;symsrv*;' + pdb_dirs]
        try:
            self.cdb = subprocess.Popen(self.shell,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError as e:
            raise CdbError('Cannot start %s -> %s' % (shell_line(self.shell), e))
        self.execute()
        if exe_dir or pdb_dirs:
            self.execute('.reload /f')

    def __enter__(self, *a):
        return self

    def __exit__(self, *a):
        try: self.cdb.communicate('q\n')
        except: pass

    def execute(self, command = None):
        '''Executes cdb :command and returns collected output.
        '''
        if command:
            self.cdb.stdin.write('%s\n' % command)
        out = ''
        def read_ch():
            c = self.cdb.stdout.read(1)
            if not c:
                raise CdbError('\n'.join((
                    '%s ->' % shell_line(self.shell),
                    'Cdb command: %s' % command,
                    'Unexpected eof: %s' % out)))
            return c
        while not out.endswith('\n0:'): out += read_ch()
        while self.cdb.stdout.read(1) != '>': pass
        return out[1:-3] # cut of prompt

    def main_module(self):
        '''Finds executable name (without extension).
        '''
        return self.execute('|').split('\n')[-1].split('\\')[-1][:-4]

    def module_info(self, module, key):
        '''Returns key-value information about :module.
        '''
        name = module.translate(string.maketrans(' .', '__'))
        for line in self.execute('lmvm%s\n' % name).split('\n'):
            if line.find(key) != -1:
                return line.split(':')[1].strip()
        raise CdbError("Attribute '%s' is not found" % key)

    def report(self):
        '''Generates text crash report (cdb-bt).
        '''
        return '\n\n'.join([
            self.execute('.exr -1'), # Error
            self.execute('.ecxr'), # context
            self.execute('kc'), # Error stack
            self.execute('~*kc'), # all threads stacks
        ])

class DumpAnalyzer(object):
    '''Provides ability to analize windows DMP dumps.
    '''

    def __init__(
        self, path, customization='default',
        version=None, build=None, branch='', verbose=0, debug=''):
        '''Initializes analizer with dump :path and :customization;
        :version, :build, :branch - optionals to speed up process;
        :verbose - maximal log level (default 0 means no logs).
        '''
        self.dump_path = path
        self.customization = customization
        self.version = version
        self.build = build
        self.branch = branch
        self.verbose = int(verbose)
        self.debug = debug.split(',')

    def log(self, message, level=0):
        '''Logs data in case of verbose mode.
        '''
        if level < self.verbose:
            sys.stderr.write('[%i] %s\n' % (level, message))

    def get_dump_information(self):
        '''Gets initial information from dump.
        '''
        with Cdb(self.dump_path) as cdb:
            self.log('Info run: ' + shell_line(cdb.shell), level=1)
            self.module = cdb.main_module()
            self.log("CDB reports main module: " + self.module, level=2)
            self.version = self.version or cdb.module_info(self.module, 'version')
            self.log("CDB reports version: " + self.version, level=2)
        self.dist = 'server' if self.module.find('server') != -1 else 'client'
        self.log('Dump information: %s (%s) %s %s ' % (
            self.module, self.dist, self.version, self.customization))
        self.build = self.build or self.version.split('.')[-1]
        if self.build == '0':
            raise UserError('Build 0 is not supported')

    def fetch_url_data(self, url, regexps, subUrl=None):
        '''Fetches data from :url by :regexp (must contain single group!).
        '''
        try:
            page = urllib2.urlopen(url).read().replace('\r\n', '').replace('\n', '')
        except urllib2.HTTPError as e:
            raise DistError('%s, url: %s' % (e, url))
        results, failures = [], []
        for regexp in regexps:
            self.log("Trying regexp '%s'" % regexp, level=2)
            for m in re.finditer(regexp, page):
                self.log("Regexp '%s' got url '%s'" % (regexp, m.group(1)), level=2)
                results.append((url, m.group(1)))
            else:
                self.log("Warning: Unable to find '%s' in %s" % (regexp, url), level=2)
                failures.append(regexp)
        if subUrl and len(failures):
            results += self.fetch_url_data(subUrl, failures)
        return results

    def fetch_urls(self):
        '''Fetches URLs of required resourses.
        '''
        out = self.fetch_url_data(
            CONFIG['dist_url'], ['''>(%s\-%s[^<]+)<''' % (self.build, self.branch)])
        if len(out) == 0:
            print "No distributive found for build %s. Dump analyze imposible" % self.build
            return False
        build_path = '%s/%s/windows/' % (out[0][1], self.customization)
        update_path = '%s/%s/updates/%s/' % (out[0][1], self.customization, self.build)
        build_url = os.path.join(CONFIG['dist_url'], build_path)
        self.log("build_url = '%s',\ndist_url = '%s'\nbuild_path = '%s'" % (
              build_url, CONFIG['dist_url'], build_path), level=2)
        suffixes = list(s % self.dist for s in CONFIG['dist_suffixes']) +\
           list(s % {'module': self.dist} for s in CONFIG['pdb_suffixes'])
        out = self.fetch_url_data(
            build_url, ('''>([a-zA-Z0-9-_\.]+%s)<''' % r for r in suffixes),
            os.path.join(CONFIG['dist_url'], update_path))
        self.dist_urls = list(os.path.join(*e) for e in out)
        self.build_path = os.path.join(CONFIG['data_dir'],  build_path)
        self.target_path = os.path.join(self.build_path, 'target')
        if not os.path.isdir(self.target_path):
            os.makedirs(self.target_path)
        return True

    def download_url_data(self, url, local):
        '''Downloads file from :url to :local directory, apply :processor if any.
        '''
        path = os.path.join(local, os.path.basename(url))
        if not os.path.isfile(path):
            self.log('Download: %s to %s' % (url, path))
            with open(path, 'wb') as f:
                f.write(urllib2.urlopen(url).read())
        else:
            self.log('Already downloaded: %s' % path, level=1)
        return path

    def find_files_iter(self, condition, path=None):
        '''Searches file by :condition in :path (build directory by default).
        '''
        path = path or self.build_path
        for root, dirs, files in os.walk(path):
            for name in files:
                if condition(name):
                    yield os.path.join(root, name)

    def find_file(self, name, path=None):
        '''Searches file by :name in :path (build directory by default).
        '''
        path = path or self.build_path
        for path in self.find_files_iter(lambda n: n == name, path):
            return path
        raise DistError("No such file '%s' in '%s'" % (name, path))

    def module_dir(self):
        '''Returns executable module directory (performs search if needed).
        '''
        if not hasattr(self, '_module_dir'):
            self._module_dir = os.path.dirname(self.find_file(self.module + '.exe'))
        return self._module_dir

    def extract_dist(self, path):
        '''Extract distributive by :path based in it's format:
           .msi - just extracts to the 'target' directory;
           .exe - extracts msi by wix toolset and treats msi normaly;
           .zip - just extract to the target exe directory.
        '''
        def run(*command):
            try:
                return subprocess.check_output(command)
            except (IOError, WindowsError, subprocess.CalledProcessError) as e:
                raise DistError('Cannot run: %s -> %s' % (shell_line(command), e))

        if path.endswith('.exe'):
            wix_dir = os.path.join(os.path.dirname(path), 'wix');
            if not os.path.isdir(wix_dir):
                os.mkdir(wix_dir)
                self.log('Unpack %s to %s' % (path, wix_dir), level=1)
                run('dark', '-x', wix_dir, path)
            msi_name = os.path.basename(path.replace('.exe', '.msi'))
            return self.extract_dist(self.find_file(msi_name, wix_dir))

        if path.endswith('.msi'):
            p, d = path.replace('/', '\\'), self.target_path.replace('/', '\\')
            self.log('Extract %s to %s' % (p, d), level=1)
            return run('msiexec', '-a', p, '/qb', 'TARGETDIR=' + d)

        if path.endswith('.zip'):
            d = self.module_dir()
            self.log('Unzip %s to %s' % (path, d), level=1)
            return run(CONFIG['zip_path'], 'x', path, '-o' + d, '-y', '-aos')

        raise DistError('Can not extract: %s' % path)

    def download_dists(self):
        '''Downloads required distributives.
        '''
        if not self.dist_urls:
           raise DistError('There are no distributive URLs avaliable')
        self.log('Found dists urls:\n%s' % '\n'.join(self.dist_urls), level=1)
        try:
            for url in self.dist_urls:
                path = self.download_url_data(url, self.build_path)
                self.extract_dist(path)
            self.log('Download has finished: %s' % self.module_dir(), level=2)
        except DistError:
            if 'keep' not in self.debug:
                def logError(f, p, e):
                    self.log("Warning: %s '%s': %s" % (f, p, repr(e)), level=1)
                shutil.rmtree(self.build_path, onerror=logError)
            raise
        if 'copy' in self.debug or 'cp' in self.debug:
            shutil.copy(self.dump_path, self.module_dir())

    def generate_report(self, asString=False):
        '''Generates report using cdb with debug information.
        '''
        report_path = report_name(self.dump_path)
        self.log('Loading debug information: ' + self.module_dir())
        pdb_dirs = ';'.join(set(os.path.dirname(f) for f in
            self.find_files_iter(lambda n: n.lower().endswith(".pdb"))))
        with Cdb(self.dump_path, self.module_dir(), pdb_dirs) as cdb:
            self.log('Debug run: ' + shell_line(cdb.shell), level=1)
            self.log('Generating report: ' + report_path)
            report = cdb.report()
            with open(report_path, 'w') as report_file:
                report_file.write(report)
        return report if asString else report_path

def analyseDump(*args, **kwargs):
    '''Generated cdb-bt report based on dmp file.
    Note: Returns right away in case if dump is already analized.
    Returns: cdb-bt report path.
    '''
    def resultDict(dump, text):
        return dict(
            component = dump.dist,
            dump = text
        )
    format = kwargs.pop('format', 'path')  # possible values: path, str, dict
    if not format in {'path', 'str', 'dict'}:
        raise UserError("Wrong format value: %s" % format)
    dump = DumpAnalyzer(*args, **kwargs)
    report = report_name(dump.dump_path)
    if os.path.isfile(report) and 'rewrite' not in kwargs.get('debug', ''):
        if format == 'dict':
            dump.get_dump_information()
            return resultDict(dump, open(report, 'r').read())
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
    return resultDict(dump, reportText) if format == 'dict' else reportText

def main():
    args, kwargs = list(), dict()
    for arg in sys.argv[1:]:
        s = arg.split('=', 2)
        if len(s) == 1: args.append(s[0])
        else: kwargs[s[0]] = s[1]
    try:
        print analyseDump(*args, **kwargs)
    except Error as e:
        if 'throw' in kwargs.get('debug', ''): raise
        sys.stderr.write('%s: %s\n' % (type(e).__name__, e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stderr.write('Interrupted\n')

if __name__ == '__main__':
    main()

