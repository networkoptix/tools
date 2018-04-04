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
from typing import List, Callable

import utils

logger = logging.getLogger(__name__)

DIST_URLS = [
    'http://beta.enk.me/beta-builds/daily/',
    'http://beta.networkoptix.com/beta-builds/daily/',
]

DIST_SUFFIXES = [
    """x64[a-z-_]+%s(-only)?\.(msi|exe)""",
    """%s-[0-9\.-_]+-win64[a-z-_]*\.(exe|msi)""",
]

PDB_SUFFIXES = [
    """x64[a-z-_]+windows-pdb-(all|apps|%(module)s|libs)\.zip""",
    """(%(module)s|libs)_debug-[0-9\.-_]+-win64[a-z-_]*\.zip""",
]

CUSTOMIZATIONS = (
    'default',
    'default_cn',
    'default_zh_CN',
    'digitalwatchdog',
    'ionetworks',
    'ipera',
    'hanwha',
    'senturian',
    'systemk',
    'vista',
    'vmsdemoblue',
    'vmsdemoorange',
)

CUSTOMIZATION_ALIASES = {
	'nx': 'default',
	'networkoptix': 'default',
    'dw': 'digitalwatchdog',
}


def deduce_customization(dump_path):
    for c in CUSTOMIZATIONS:
        if c in dump_path:
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


def report_name(dump_path: str, safe: bool = False):
    """Generates report name based on dump name.
    """
    dump_ext = '.dmp'
    if not dump_path.lower().endswith(dump_ext):
        if safe:
            return ''  # to calls where exceptions aren't wanted
        raise UserError('Only *%s dumps are supported, rejected: %s' % (
            dump_ext, dump_path))
    report_ext = '.cdb-bt'
    return dump_path[:-len(dump_ext)] + report_ext


def clear_cache(cache_dir: str, keep_files: str):
    existing = set(os.listdir(cache_dir))
    for name in keep_files:
        existing.discard(report_name(name, True))
    for name in existing:
        try:
            os.remove(os.path.join(cache_dir, name))
        except IOError:
            pass


def shell_line(command: List[str]):
    return ' '.join('"%s"' % a if (' ' in a) or ('\\' in a) else a for a in command)


class Cdb:
    """Cdb program driver to analyze DMP files.
    """

    def __init__(self, dump, exe_dir: str = '', pdb_dir: str = ''):
        """Starts up cdb with :dump, :exe_dir and :pdb_dir.
        """
        self.shell = ['cdb', '-z', dump]
        if exe_dir:
            self.shell += ['-i', exe_dir]

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
            self.cdb.stdin.write(command.encode() + b'\n')
            self.cdb.stdin.flush()

        out = ''
        while not out.endswith('\n0:'):
            # TODO: Implement read timeout, so we are sure it newer blocks forever.
            c = self.cdb.stdout.read(1)
            if not c:
                raise CdbError('\n'.join((
                    '%s ->' % shell_line(self.shell),
                    'Cdb command: %s' % command,
                    'Unexpected eof: %s' % out)))

            out += c.decode()

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


class DumpAnalyzer(object):
    """Provides ability to analize windows DMP dumps.
    """

    def __init__(
            self, cache_directory, dump_path,
            customization: str = '', version: str = '', build: str = None, branch: str = '',
            subprocess_timout_s: int = 10, debug_mode: bool = False,
            visual_studio: bool = False):
        """Initializes analizer with dump :path and :customization;
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
        self.subprocess_timout_s = subprocess_timout_s
        self.module, self.dist, self.build_path, self.target_path = None, None, None, None

        deduced = deduce_customization(dump_path)
        if not self.customization:
            if not deduced:
                raise UserError('Customization is not selected and can not be deduced')

            logger.debug('Deduced customization [%s] selected for: %s' % (deduced, dump_path))
            self.customization = deduced
            return

        if deduced and self.customization != deduced:
            logger.warning('Selected customization [%s] does not match deduced [%s] for: %s' % (
                self.customization, deduced, dump_path))

    def get_dump_information(self):
        """Gets initial information from dump.
        """
        with Cdb(self.dump_path) as cdb:
            self.module = cdb.main_module()
            logger.debug("CDB reports main module: " + self.module)
            self.version = self.version or cdb.module_info(self.module, 'version')
            logger.debug("CDB reports version: " + self.version)

        self.dist = 'server' if self.module.find('server') != -1 else 'client'
        logger.info('Dump information: %s (%s) %s %s ' % (
            self.module, self.dist, self.version, self.customization))

        self.build = self.build or self.version.split('.')[-1]
        if self.build == '0':
            raise UserError('Build 0 is not supported for: ' + self.dump_path)

    def fetch_url_data(self, url: str, regexps: List[str], sub_url: str = '') -> List[str]:
        """Fetches data from :url by :regexp (must contain single group!).
        """
        try:
            page = urllib.request.urlopen(url).read().decode().replace('\r\n', '').replace('\n', '')
        except urllib.error.HTTPError as error:
            raise DistError('%s, url: %s' % (error, url))

        results, failures = [], []
        for regexp in regexps:
            for m in re.finditer(regexp, page):
                item = m.group(1)
                logger.debug("Found distributive '%s' in: %s" % (item, url))
                results.append((url, item))
            else:
                logger.debug("Failed to get '%s' in: %s" % (regexp, url))
                failures.append(regexp)

        if sub_url and len(failures):
            results += self.fetch_url_data(sub_url, failures)

        return results

    def fetch_urls(self) -> bool:
        """Fetches URLs of required resources.
        """
        dist_url, out = None, None
        for url in DIST_URLS:
            out = self.fetch_url_data(
                url, [""">(%s\-%s[^<]*)<""" % (self.build, re.escape(self.branch))])

            if len(out) > 0:
                dist_url = url
                break

        if not dist_url:
            raise DistError("No distributive found for build %s, analyze impossible" % self.build)

        build_path = '%s/%s/windows/' % (out[0][1], self.customization)
        update_path = '%s/%s/updates/%s/' % (out[0][1], self.customization, self.build)
        build_url = os.path.join(dist_url, build_path)
        suffixes = list(s % self.dist for s in DIST_SUFFIXES) + \
                   list(s % {'module': self.dist} for s in PDB_SUFFIXES)

        out = self.fetch_url_data(
            build_url, (""">([a-zA-Z0-9-_\.]+%s)<""" % r for r in suffixes),
            os.path.join(dist_url, update_path))

        self.build_path = os.path.join(self.cache_directory, build_path)
        self.target_path = os.path.join(self.build_path, 'target')
        if not os.path.isdir(self.target_path):
            os.makedirs(self.target_path)

        return list(os.path.join(*url) for url in out)

    def download_url_data(self, url: str, local: str) -> str:
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

    def extract_dist(self, path):
        """Extract distributive by :path based in it's format:
           .msi - just extracts to the 'target' directory;
           .exe - extracts msi by wix toolset and treats msi normally;
           .zip - just extract to the target exe directory.
        """

        def run(command, retry_code = 0, retry_count = 0):
            try:
                logger.debug(shell_line(command))
                return subprocess.check_output(command, timeout=self.subprocess_timout_s)
            except subprocess.CalledProcessError as error:
                if retry_count and 'status ' + str(retry_code) in str(error):
                    time.sleep(1)
                    run(command, retry_code, retry_count - 1)
                else:
                    raise
            except (IOError, WindowsError, subprocess.CalledProcessError) as error:
                raise DistError(error)

        if path.endswith('.exe'):
            wix_dir = os.path.join(os.path.dirname(path), 'wix')
            if not os.path.isdir(wix_dir):
                os.mkdir(wix_dir)
                run(['dark', '-x', wix_dir, path])

            return self.extract_dist(self.find_file('.msi', wix_dir))

        if path.endswith('.msi'):
            p, d = path.replace('/', '\\'), self.target_path.replace('/', '\\')
            return run(
                ['msiexec', '-a', os.path.abspath(p), '/qb', 'TARGETDIR=' + os.path.abspath(d)],
                retry_code=1618, retry_count=self.subprocess_timout_s * 2)

        if path.endswith('.msi') or path.endswith('.zip'):
            return run(['7z', 'x', path, '-o' + self.module_dir(), '-y', '-aos'])

        raise DistError('Can not extract: %s' % path)

    def download_dists(self):
        """Downloads required distributions.
        """
        urls = self.fetch_urls()
        if not urls:
            raise DistError('There are no distributive URLs available')

        # TODO: Implement some directory locking for safety.
        try:
            for url in urls:
                path = self.download_url_data(url, self.build_path)
                self.extract_dist(path)
        except DistError:
            if not self.debug_mode:
                logger.debug('Clean up download dir: ' + self.build_path)
                shutil.rmtree(self.build_path, onerror=lambda f, p, ex: logger.error(
                    "%s '%s': %s" % (f, p, repr(ex))))
            raise

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

    def generate_report(self, report_path):
        """Generates report using cdb with debug information.
        """
        logger.info('Loading debug information from: ' + self.module_dir())
        pdb_dirs = ';'.join(set(os.path.dirname(f) for f in
                                self.find_files_iter(lambda n: n.lower().endswith(".pdb"))))

        with Cdb(self.dump_path, self.module_dir(), pdb_dirs) as cdb:
            logger.debug('Generating report: ' + report_path)
            report = cdb.report()
            with open(report_path, 'w') as report_file:
                report_file.write(report)

        logger.info('Report is written to: ' + report_path)
        return report


def analyse_dump(generate: bool = True, *args, **kwargs):
    """Generated cdb-bt report based on dmp file.
    Note: Returns right away in case if dump is already analyzed.
    Returns: cdb-bt report path.
    """
    dump = DumpAnalyzer(*args, **kwargs)
    if generate:
        report_path = report_name(dump.dump_path)
        if os.path.isfile(report_path):
            logger.warning('Already processed: ' + report_path)
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
    parser.add_argument('dump_path', help='dmp file to analyze')
    parser.add_argument('customization', nargs='?', help='default: auto deduce by name')
    parser.add_argument('-g', '--generate', action='store_true', default=False,
                        help='generate report instead of launching Visual Studio')
    parser.add_argument('-D', '--debug-mode', action='store_true', default=False)
    parser.add_argument('-b', '--branch', default='')
    parser.add_argument('-d', '--cache-directory', default='./dumptool')

    arguments = parser.parse_args()
    logging.basicConfig(
        level=(logging.DEBUG if arguments.debug_mode else logging.INFO),
        format='%(asctime)s %(levelname)8s: %(message)s', stream=sys.stdout)

    try:
        analyse_dump(**vars(arguments))

    except Error as e:
        if arguments.debug_mode:
            raise

        logger.critical(e)
        sys.exit(1)

    except KeyboardInterrupt:
        sys.stderr.write('Interrupted\n')
