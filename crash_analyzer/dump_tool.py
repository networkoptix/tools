#!/usr/bin/env python3
"""Automatic windows dump analyser tool

Generates test report (cdb-bt) based on dump (dmp). Binaries and debug
information gets automatically from jenkins. Takes about a minute to analyse
(several more if debug information is required).
"""

import logging
import os
import re
import shutil
import subprocess
import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
import http.client
import traceback
from typing import List, Callable
if os.name == 'nt':
    import msvcrt

logger = logging.getLogger(__name__)


CDB_CACHE_DIRECTORIES = [
    'C:/ProgramData/dbg/sym',
    'C:/Program Files (x86)/Windows Kits/10/Debuggers/x64/sym',
]

CDB_KNOWN_ERRORS = [
    'Minidump does not have system info',
    'invalid file format',
    'Catastrophic failure',
]

DIST_URLS = [
    'http://beta.enk.me/beta-builds/daily/',
    'http://beta.networkoptix.com/beta-builds/daily/',
]

DIST_SUFFIXES = [
    r'x64[a-z-_]+%s(-only)?\.(msi|exe)',
    r'%s-[0-9\.-_]+-(win|windows_x)(86|64)[a-z-_]*\.(exe|msi)',
]

PDB_SUFFIXES = [
    r'x64[a-z-_]+windows-pdb-(all|apps|%(module)s|libs)\.zip',
    r'(%(module)s|libs)_debug-[0-9\.-_]+-(win|windows_x)(86|64)[a-z-_]*\.zip',
]

CUSTOMIZATIONS = (
    'cox',
    'default',
    'default_cn',
    'default_zh_CN',
    'digitalwatchdog',
    'digitalwatchdog_global',
    'hanwha',
    'ionetworks',
    'ipera',
    'nutech',
    'ras',
    'senturian',
    'systemk',
    'ust',
    'vista',
    'vmsdemoblue',
    'vmsdemoorange',
    'metavms',
    'viveex',
)

CUSTOMIZATION_ALIASES = {
    'nx': 'default',
    'networkoptix': 'default',
    'dw': 'digitalwatchdog',
}


def deduce_customization(dump_path):
    for c in reversed(CUSTOMIZATIONS):
        if '-{}'.format(c) in dump_path:
            return c

    return None


class Error(Exception):
    """Base error type.
    """
    pass


class CdbError(Error):
    """Cdb driver related error.
    """
    pass


class UserError(Error):
    """Invalid usage, e.g. unsupported format or build number.
    """
    pass


class DistError(Error):
    """Distribution related errors, e.g. distribution in not found or invalid.
    """
    pass


def report_name(dump_path: str, empty_on_failure: bool = False) -> str:
    """Generates report name based on dump name.
    """
    dump_ext = '.dmp'
    if not dump_path.lower().endswith(dump_ext):
        if empty_on_failure:
            return ''  # < For calls where exceptions aren't wanted.
        raise UserError('Only *%s dumps are supported, rejected: %s' % (
            dump_ext, dump_path))
    report_ext = '.cdb-bt'
    return dump_path[:-len(dump_ext)] + report_ext


def shell_line(command: List[str]):
    return ' '.join('"%s"' % a if (' ' in a) or ('\\' in a) else a for a in command)


class CdbSession:
    """Cdb program driver to analyze DMP files.
    """

    def __init__(self, dump, exe_dir: str = '', pdb_dir: str = ''):
        """Starts up cdb with :dump, :exe_dir and :pdb_dir.
        """
        self.shell = ['cdb', '-z', dump]
        if exe_dir:
            self.shell += ['-i', exe_dir]
            if not pdb_dir:
                pdb_dir = exe_dir

        if pdb_dir:
            self.shell += ['-y', 'srv*;symsrv*;' + pdb_dir]

        try:
            logger.debug(shell_line(self.shell))
            self.cdb = subprocess.Popen(self.shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError as error:
            raise CdbError('Cannot start %s -> %s' % (shell_line(self.shell), error))

        self.execute()
        if exe_dir or pdb_dir:
            self.execute('.reload /f')

    def __enter__(self, *a):
        return self

    def __exit__(self, *a):
        try:
            self.cdb.communicate(b'q\n')
        except Exception as error:
            logger.warning('Unable to exit cdb:', error)

    def execute(self, command: str = ''):
        """Executes cdb :command and returns collected output.
        """
        if command:
            logger.debug('Cdb execute: ' + command.strip())
            self.cdb.stdin.write(command.encode() + b'\n')
            self.cdb.stdin.flush()

        out = ''
        while not (out.endswith('\n0:') or out.endswith('\n?:')):
            # TODO: Implement read timeout, so we are sure it newer blocks forever.
            c = self.cdb.stdout.read(1)
            if not c:
                logger.debug('Unexpected EOF: %s' % out)
                raise CdbError('{} ->\n{}'.format(shell_line(self.shell), out))

            out += c.decode()
            for error in CDB_KNOWN_ERRORS:
                if error in out:
                    raise CdbError('{} -> {}'.format(shell_line(self.shell), error))

        while self.cdb.stdout.read(1) != b'>':
            pass

        return out[1:-3]  # < Cut of prompt.

    def main_module(self):
        """Finds executable name (without extension).
        """
        return self.execute('|').split('\n')[-1].split('\\')[-1][:-4]

    def module_info(self, module: str, key: str):
        """Returns key-value information about :module.
        """
        name = module.translate(str.maketrans(' .', '__'))
        for line in self.execute('lmvm%s\n' % name).split('\n'):
            if line.find(key) != -1:
                return line.split(':')[1].strip()
        raise CdbError("Attribute '%s' is not found" % key)

    def report(self):
        """Generates text crash report (cdb-bt).
        """
        return '\n\n'.join([
            self.execute('.exr -1'),  # < Error.
            self.execute('.ecxr'),  # < Context.
            self.execute('kc'),  # < Error stack.
            self.execute('~*kc'),  # < All threads stacks.
        ])


class FileLock:
    """File system lock file.
    """
    def __init__(self, path: str, timeout_s: float = 1):
        self.path = path
        self.timeout_s = timeout_s

    def __enter__(self):
        self.handle = open(self.path, 'w+')
        start = time.monotonic()
        while True:
            try:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_RLCK, 1)
            except OSError:
                if time.monotonic() - start > self.timeout_s:
                    self.handle.close()
                    raise DistError('Unable to lock file "{}" in {} seconds'
                                    .format(self.path, self.timeout_s))
            else:
                return self

    def __exit__(self, *args):
        msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        self.handle.close()


class DumpAnalyzer:
    """Provides ability to analyze windows DMP dumps.
    """
    def __init__(
            self, cache_directory: str, dump_path: str,
            customization: str = '', version: str = '', build: str = None, branch: str = '',
            subprocess_timeout_s: int = 20, debug_mode: bool = False,
            visual_studio: bool = False):
        """Initializes analyzer with dump :path and :customization;
        :version, :build, :branch - optionals to speed up process.
        """
        self.cache_directory = cache_directory
        self.dump_path = dump_path
        self.customization = CUSTOMIZATION_ALIASES.get(customization, customization)
        self.version = version
        self.build = build
        self.branch = branch
        self.debug_mode = debug_mode
        self.visual_studio = visual_studio
        self.subprocess_timeout_s = subprocess_timeout_s
        self.module = None
        self.dist = None
        self.base_build_path = None
        self.build_path = None
        self.target_path = None

        deduced = deduce_customization(dump_path)
        if not self.customization:
            if not deduced:
                raise UserError('Customization is not selected and can not be deduced for: %s'
                                % dump_path)

            logger.debug('Deduced customization [%s] selected for: %s' % (deduced, dump_path))
            self.customization = deduced
            return

        if deduced and self.customization != deduced:
            logger.warning('Selected customization [%s] does not match deduced [%s] for: %s' % (
                self.customization, deduced, dump_path))

    def get_dump_information(self):
        """Gets initial information from dump.
        """
        with CdbSession(self.dump_path) as cdb:
            self.module = cdb.main_module()
            logger.debug("CDB reports main module: " + self.module)
            self.version = self.version or cdb.module_info(self.module, 'version')
            logger.debug("CDB reports version: " + self.version)

        self.dist = 'server' if self.module.find('server') != -1 else 'client'
        logger.debug('Dump information: %s (%s) %s %s ' % (
            self.module, self.dist, self.version, self.customization))

        self.build = self.build or self.version.split('.')[-1]
        if not self.build or self.build == '0':
            raise UserError('Build number is not specified for: ' + self.dump_path)

    def fetch_url_data(self, url: str, regexps: List[str], sub_url: str = '') -> List[str]:
        """Fetches data from :url by :regexp (must contain single group!).
        """
        try:
            page = urllib.request.urlopen(url).read().decode().replace('\r\n', '').replace('\n', '')
        except (urllib.error.HTTPError, http.client.IncompleteRead, urllib.error.URLError) as error:
            raise DistError('%s, url: %s' % (error, url))

        results, failures = [], []
        for regexp in regexps:
            for m in re.finditer(regexp, page):
                item = m.group(1)
                logger.debug("Found distributive '%s' in: %s" % (item, url))
                results.append((url, item))
            else:
                failures.append(regexp)

        if sub_url and len(failures):
            results += self.fetch_url_data(sub_url, failures)

        return results

    def fetch_urls(self) -> bool:
        """Fetches URLs of required resources.
        """
        dist_url, out = None, None
        for url in DIST_URLS:
            logger.debug('Search for dist on {}'.format(url))
            try:
                out = self.fetch_url_data(
                    url, [r'>(%s\-%s[^<]*)<' % (self.build, re.escape(self.branch))])
                if len(out) > 0:
                    dist_url = url
                    break
            except DistError as e:
                logger.debug(e)

        if not dist_url:
            raise DistError("No distributive directory is found for build %s on %r" % (
                self.build, DIST_URLS))

        build_path = '%s/%s/windows/' % (out[0][1], self.customization)
        update_path = '%s/%s/updates/%s/' % (out[0][1], self.customization, self.build)
        build_url = os.path.join(dist_url, build_path)
        suffixes = list(s % self.dist for s in DIST_SUFFIXES) + list(s % {'module': self.dist} for s in PDB_SUFFIXES)

        out = self.fetch_url_data(
            build_url, (r'>([a-zA-Z0-9-_\.]+%s)<' % r for r in suffixes),
            os.path.join(dist_url, update_path))

        if not out:
            raise DistError("No distributive files are found for build %s on %r" % (
                self.build, DIST_URLS))

        self.base_build_path = os.path.join(self.cache_directory, build_path)
        return list(os.path.join(*url) for url in out)

    @staticmethod
    def download_url_data(url: str, local: str) -> str:
        """Downloads file from :url to :local directory, apply :processor if any.
        """
        path = os.path.join(local, os.path.basename(url))
        if not os.path.isfile(path):
            logger.info('Download: %s to %s' % (url, path))
            with open(path, 'wb') as f:
                f.write(urllib.request.urlopen(url).read())
        else:
            logger.debug('Already downloaded: %s' % path)

        return path

    def find_files_iter(self, condition: Callable, path: str = None):
        """Searches file by :condition in :path (build directory by default).
        """
        path = path or self.build_path
        for root, dirs, files in os.walk(path):
            for name in files:
                if condition(name):
                    yield os.path.join(root, name)

    def find_file(self, name: str, path: str = None) -> str:
        """Searches file by :name in :path (build directory by default).
        """
        path = path or self.build_path
        for path in self.find_files_iter(lambda n: n.endswith(name), path):
            return path

        raise DistError("No such file '%s' in '%s'" % (name, path))

    def module_dir(self) -> str:
        """Returns executable module directory (performs search if needed).
        """
        if not hasattr(self, '_module_dir'):
            self._module_dir = os.path.dirname(self.find_file(self.module + '.exe'))

        return self._module_dir

    def extract_dist(self, path: str):
        """Extract distributive by :path based in it's format:
           .msi - just extracts to the 'target' directory;
           .exe - extracts msi by wix toolset and treats msi normally;
           .zip - just extract to the target exe directory.
        """

        def run(command, retry_code=0, retry_count=0):
            try:
                logger.debug(shell_line(command))
                return subprocess.check_output(command, timeout=self.subprocess_timeout_s)
            except subprocess.CalledProcessError as error:
                if retry_count and 'status ' + str(retry_code) in str(error):
                    time.sleep(1)
                    run(command, retry_code, retry_count - 1)
                else:
                    raise DistError(str(error))
            except (IOError, WindowsError) as error:
                raise DistError(error)

        if path.endswith('.exe'):
            wix_dir = os.path.join(os.path.dirname(path), 'wix')
            if not os.path.isdir(wix_dir):
                os.mkdir(wix_dir)
                run(['dark', '-x', wix_dir, path])

            wix_parts = list(self.find_files_iter(
                lambda n: (n.endswith('.msi') or n.endswith('.cab')), wix_dir))
            if not wix_parts:
                raise DistError("WIX installer '%s' does not contain file archives" % path)

            return [self.extract_dist(part) for part in wix_parts]

        if path.endswith('.cab'):
             return run(['7z', 'x', path, '-o' + self.target_path + '/cabs', '-y', '-aos'])

        if path.endswith('.msi'):
            p, d = path.replace('/', '\\'), self.target_path.replace('/', '\\')
            return run(
                ['msiexec', '-a', os.path.abspath(p), '/qb', 'TARGETDIR=' + os.path.abspath(d)],
                retry_code=1618, retry_count=self.subprocess_timeout_s * 2)

        if path.endswith('.zip'):
            return run(['7z', 'x', path, '-o' + self.module_dir(), '-y', '-aos'])

        raise DistError('Can not extract: %s' % path)

    def download_dists(self):
        """Downloads required distributions.
        """
        try:
            urls = self.fetch_urls()
        except (http.client.HTTPException, urllib.error.URLError) as e:
            raise DistError(str(e))

        self.build_path = os.path.join(self.base_build_path, self.dist)
        self.target_path = os.path.join(self.build_path, 'target')
        try:
            os.makedirs(self.build_path)
        except FileExistsError:
            pass

        with FileLock(
            os.path.join(self.base_build_path, self.dist + '-lock'),
            self.subprocess_timeout_s * len(urls)
        ) as lock:
            self.download_dist_urls(urls)
            self.prepare_dist_for_debug()

    def download_dist_urls(self, urls):
        try:
            logger.debug('Skip download of existing build: ' + self.module_dir())
            return
        except DistError:
            pass

        if not os.path.isdir(self.target_path):
            os.makedirs(self.target_path)

        try:
            for url in urls:
                path = self.download_url_data(url, self.build_path)
                self.extract_dist(path)

        except Exception:
            logger.debug('Unable to get build "{}": {}'.format(
                self.build_path, traceback.format_exc()))
            if not self.debug_mode:
                try:
                    logger.debug('Clean up download directory: ' + self.build_path)
                    shutil.rmtree(self.build_path)
                except Exception:
                    logger.error('Unable to cleanup: {}'.format(traceback.format_exc()))
            raise

    def prepare_dist_for_debug(self):
        """Move all PDBs into the root so CDB and VS can use them.
        """
        moved = []
        for item in self.find_files_iter(lambda n: n.lower().split('.')[-1] in ['dll', 'pdb']):
            if not os.path.isfile(os.path.join(self.module_dir(), os.path.basename(item))):
                shutil.move(item, self.module_dir())
                moved.append(item[len(self.module_dir()):])

        if moved:
            logger.debug('Move files to module: ' + ', '.join(moved))

    def run_visual_studio(self):
        """Open dump in visual studio.
        """
        short_name = 'dump-%s.dmp' % hashlib.sha256(self.dump_path.encode()).hexdigest()[20:]
        short_path = os.path.join(self.module_dir(), short_name)
        logger.debug("Copy dump '%s' to '%s'" % (self.dump_path, short_path))
        shutil.copy(self.dump_path, short_path)

        os.chdir(self.module_dir())
        logger.info('Open with Visual Studio in: %s' % self.module_dir())
        subprocess.Popen(['devenv', short_name])

    def generate_report(self, report_path: str) -> str:
        """Generates report using cdb with debug information.
        """
        logger.info('Loading debug information from: ' + self.module_dir())
        with CdbSession(self.dump_path, self.module_dir()) as cdb:
            logger.debug('Generating report: ' + report_path)
            report = cdb.report()
            with open(report_path, 'w') as report_file:
                report_file.write(report)

        logger.info('Report is written to: ' + report_path)
        return report


def analyse_dump(generate: bool = True, *args, **kwargs) -> str:
    """Generated cdb-bt report based on dmp file.
    Note: Returns right away in case if dump is already analyzed.
    Returns: cdb-bt report path.
    """
    dump = DumpAnalyzer(*args, **kwargs)
    if generate:
        report_path = report_name(dump.dump_path)
        if os.path.isfile(report_path):
            logger.info('Already processed: ' + report_path)
            with open(report_path, 'r') as f:
                return f.read()

        dump.get_dump_information()
        dump.download_dists()
        return dump.generate_report(report_path)

    dump.get_dump_information()
    dump.download_dists()
    dump.run_visual_studio()


if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('dump_path', help='dmp file path to analyze')
    parser.add_argument('customization', nargs='?', help='default: auto deduce by name')
    parser.add_argument('-g', '--generate', action='store_true', default=False,
                        help='generate report instead of launching Visual Studio')
    parser.add_argument('-d', '--cache-directory', default='./dump_tool_cache')
    parser.add_argument('-b', '--branch', default='')
    parser.add_argument('-V', '--version', default='')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='enable all logs')
    parser.add_argument('-D', '--debug-mode', action='store_true', default=False,
                        help='use for this script debug only')

    arguments = parser.parse_args()
    logging.basicConfig(
        level=(logging.DEBUG if arguments.verbose else logging.INFO),
        format='%(asctime)s %(levelname)8s: %(message)s', stream=sys.stdout)

    del arguments.verbose
    try:
        analyse_dump(**vars(arguments), subprocess_timeout_s=60)

    except Error as e:
        if arguments.debug_mode:
            raise

        logger.critical(e)
        sys.exit(1)

    except KeyboardInterrupt:
        sys.stderr.write('Interrupted\n')
