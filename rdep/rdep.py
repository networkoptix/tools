#!/usr/bin/env python

import argparse
import os
import sys
import shutil
import subprocess
import tempfile
import posixpath

from rdep_config import RdepConfig, RepositoryConfig, PackageConfig
from fsutil import copy_recursive

# Workaround against rsync bug:
# all paths with semicolon are counted as remote,
# so 'rsync rsync://server/path c:\test\path' won't work on windows
def _cygwin_path(path):
    if len(path) > 1 and path[1] == ':':
        drive_letter = path[0].lower()
        return "/cygdrive/{0}{1}".format(drive_letter, path[2:].replace("\\", "/"))
    return path

def _find_root(path, file_name):
    while not os.path.isfile(os.path.join(path, file_name)):
        nextpath = os.path.dirname(path)
        if path == nextpath:
            return None
        else:
            path = nextpath

    return path

class Rdep:
    ANY_KEYWORD = "any"
    DEBUG_SUFFIX = "-debug"
    SYNC_NOT_FOUND = 0
    SYNC_FAILED = 1
    SYNC_SUCCESS = 2

    def init_repository(path, url):
        if not os.path.isdir(path):
            print >> sys.stderr, "Directory does not exists: {0}".format(path)
            return False

        if not url:
            print >> sys.stderr, "Url cannot be empty"
            return False

        try:
            config = RepositoryConfig(os.path.join(path, ROOT_CONFIG_NAME))
            config.set_url(url)
        except:
            print >> sys.stderr, "Could not init repository at {0}".format(path)
            return False

        print "Initialized repository at {0}".format(path)
        print "The repository will use URL = {0}".format(url)

        return True

    def __init__(self, root, target = None):
        self._config = RdepConfig(os.path.join(os.path.expanduser("~"), ".rdeprc"))
        self._repo_config = RepositoryConfig(os.path.join(root, ".rdep"))

        self.root = root
        self.verbose = False
        self.target = target if target else self._config.get_default_target()

    def _verbose_message(self, message):
        if self.verbose:
            print message

    def _verbose_rsync(self, command):
        self._verbose_message("Executing rsync:\n{0}".format(" ".join(command)))

    def detect_package_and_target(self, path):
        if not path.startswith(self.root):
            return None, None

        path, target = os.path.split(path)
        package = None

        while path != self.root and target:
            package = target
            path, target = os.path.split(path)

        if path == self.root:
            return target, package

        return None, None

    def _get_rsync_command(
            self,
            source,
            destination,
            show_progress = True,
            additional_args = []):

        command = [ self._config.get_rsync() ]
        command.append("-rlt")
        command.append("--delete")

        if show_progress:
            command.append("--progress")

        if not source.startswith("rsync://") and not destination.startswith("rsync://"):
            ssh = self._repo_config.get_ssh()
            if not ssh:
                ssh = self._config.get_ssh()
            if ssh:
                command.append("-e")
                command.append(ssh)

        command.append(source)
        if destination:
            command.append(destination)

        return command

    def _try_sync(self, target, package, force):
        url = self._repo_config.get_url()
        src = posixpath.join(url, target, package)
        dst = os.path.join(self.root, target, package)

        self._verbose_message(
            "root {0}\nurl {1}\ntarget {2}\npackage {3}\nsrc {4}\ndst {5}"
                .format(self.root, url, target, package, src, dst))

        config_file = tempfile.mktemp()
        command = self._get_rsync_command(
                posixpath.join(src, PackageConfig.FILE_NAME),
                _cygwin_path(config_file),
                show_progress = False)
        self._verbose_rsync(command)
        with open(os.devnull, "w") as fnull:
            if subprocess.call(command, stderr = fnull) != 0:
                return self.SYNC_NOT_FOUND

        newtime = PackageConfig(config_file).get_timestamp()
        if newtime == None:
            os.remove(config_file)
            return self.SYNC_NOT_FOUND

        time = PackageConfig(dst).get_timestamp()
        if newtime == time and not force:
            os.remove(config_file)
            return self.SYNC_SUCCESS

        if not os.path.isdir(dst):
            os.makedirs(dst)

        command = self._get_rsync_command(
                src + "/",
                _cygwin_path(dst),
                additional_args = [ "--exclude", PackageConfig.FILE_NAME]
        )
        self._verbose_rsync(command)

        if subprocess.call(command) != 0:
            os.remove(config_file)
            return self.SYNC_FAILED

        dst_config_file = os.path.join(dst, PackageConfig.FILE_NAME)
        self._verbose_message("Moving {0} to {1}".format(
                config_file, dst_config_file))
        shutil.move(config_file, dst_config_file)

        return self.SYNC_SUCCESS

    def sync_package(self, package, force):
        print "Synching {0}...".format(package)

        to_remove = None
        target = self.target

        ret = self._try_sync(target, package, force)
        if ret == self.SYNC_NOT_FOUND:
            path = os.path.join(self.root, target, package)
            if os.path.isdir(path):
                to_remove = path

            target = self.ANY_KEYWORD

            ret = self._try_sync(target, package, force)
            if ret == self.SYNC_NOT_FOUND:
                path = os.path.join(self.root, target, package)
                print >> sys.stderr, "Could not find {0}".format(package)
                return False

        if to_remove:
            print "Removing local {0}".format(to_remove)
            shutil.rmtree(to_remove)
            to_remove = None

        if ret == self.SYNC_FAILED:
            print >> sys.stderr, "Sync failed for {0}".format(package)
            return False

        if self.debug:
            ret = self._try_sync(target, package + self.DEBUG_SUFFIX, force)

            if ret == self.SYNC_NOT_FOUND:
                path = os.path.join(self.root, target, package + self.DEBUG_SUFFIX)
                if os.path.isdir(path):
                    to_remove = path
            elif ret == self.SYNC_FAILED:
                print >> sys.stderr, "Sync failed for {0}".format(package + self.DEBUG_SUFFIX)
                return False

        if to_remove:
            print "Removing local {0}".format(to_remove)
            shutil.rmtree(to_remove)

        print "Done {0}".format(package)
        return True

    def sync_packages(self, packages, force):
        for package in packages:
            if not self.sync_package(package, force):
                return False
        return True

    def upload_package(self, package):
        print "Uploading {0}...".format(package)

        url = self._repo_config.get_url()
        remote = posixpath.join(url, self.target, package)
        local = os.path.join(self.root, self.target, package)

        PackageConfig(local).update_timestamp()

        command = self._get_rsync_command(
                _cygwin_path(local) + "/",
                remote,
                additional_args = [ "--exclude", PackageConfig.FILE_NAME]
        )

        self._verbose_rsync(command)

        if subprocess.call(command) != 0:
            print >> sys.stderr, "Could not upload {0}".format(package)
            return False

        command = self._get_rsync_command(
                _cygwin_path(os.path.join(local, PackageConfig.FILE_NAME)),
                remote,
                show_progress = False
        )

        self._verbose_rsync(command)

        if subprocess.call(command) != 0:
            print "Could not upload {0}".format(package)
            return False

        print "Done {0}".format(package)
        return True

    def upload_packages(self, packages):
        for package in packages:
            package_name = package + self.DEBUG_SUFFIX if self.debug else package
            if not self.upload_package(package_name):
                return False
        return True

    def locate_package(self, package):
        package_config_path = (lambda path: os.path.join(path, PackageConfig.FILE_NAME))

        if self.debug:
            path = os.path.join(self.root, self.target, package + self.DEBUG_SUFFIX)
            if os.path.exists(package_config_path(path)):
                return path

        path = os.path.join(self.root, self.target, package)
        if os.path.exists(package_config_path(path)):
            return path

        any_target = self.ANY_KEYWORD

        if self.debug:
            path = os.path.join(self.root, any_target, package + DEBUG_SUFFIX)
            if os.path.exists(package_config_path(path)):
                return path

        path = os.path.join(self.root, any_target, package)
        if os.path.exists(package_config_path(path)):
            return path

        return None

    def list_packages(self):
        url = self._repo_config.get_url()
        url = posixpath.join(url, self.target) + "/"

        command = [ self._config.get_rsync(), "--list-only", url ]
        self._verbose_rsync(command)
        try:
            output = subprocess.check_output(command)
        except:
            print "Could not list packages for {0}".format(self.target)
            return False

        for line in output.split('\n'):
            pos = line.rfind(' ')
            if pos >= 0:
                line = line[pos + 1:]

            if line and line != ".":
                print line

        return True

    def print_path(self, package):
        path = self.locate_package(package)
        if not path:
            print >> sys.stderr, "Package {0} not found.".format(package)
        print path

    def copy_package(self, package, destination):
        package_dir = self.locate_package(package)
        if not package_dir:
            print >> sys.stderr, "Could not locate package {0}".format(package)
            return False

        config = PackageConfig(os.path.join(package_dir, self.PACKAGE_CONFIG_NAME))
        copy_list = config.get_copy_list()

        for dst, sources in copy_list.items():
            if dst in [ "bin", "lib" ]:
                dst = os.path.join(dst, "debug" if debug else "release")
            dst_dir = os.path.join(destination, dst)

            for src in sources:
                src = os.path.join(package_dir, src)
                print "Copying {0} to {1}".format(src, dst_dir)
                if not os.path.isdir(dst_dir):
                    os.makedirs(dst_dir)
                copy_recursive(src, dst_dir)

        return True

    def copy_packages(self, packages, destination):
        success = True

        for package in packages:
            if not copy_package(root, target, package, destination, debug):
                return False

        return success

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target",       help="Target classifier.")
    parser.add_argument("--root",               help="Repository root.")
    parser.add_argument("-d", "--debug",        help="Sync debug version.",                 action="store_true")
    parser.add_argument("-f", "--force",        help="Force sync.",                         action="store_true")
    parser.add_argument("-u", "--upload",       help="Upload package to the repository.",   action="store_true")
    parser.add_argument("-v", "--verbose",      help="Additional debug output.",            action="store_true")
    parser.add_argument("-l", "--list",         help="List packages for target.",           action="store_true")
    parser.add_argument("--print-path",         help="Print package dir and exit.",         action="store_true")
    parser.add_argument("--copy", metavar="DIR", help="Copy package resources")
    parser.add_argument("--init", metavar="URL", help="Init repository in the current dir with the specified URL.")
    parser.add_argument("packages", nargs='*',  help="Packages to sync.",   default="")

    args = parser.parse_args()

    if args.init:
        return Rdep.init_repository(os.getcwd(), args.init)

    root = args.root
    if not root:
        root = _find_root(os.getcwd(), RepositoryConfig.FILE_NAME)

    rdep = Rdep(root, args.target)
    rdep.verbose = args.verbose
    rdep.debug = args.debug

    if not rdep.target:
        print >> sys.stderr, "The default target is not set"
        return False

    packages = args.packages
    if root:
        detected_target, package = rdep.detect_package_and_target(os.getcwd())
        if detected_target:
            rdep.target = detected_target
        if not packages and package:
            packages = [ package ]

    if args.print_path:
        return rdep.print_path(packages[0])
    elif args.upload:
        return rdep.upload_packages(packages)
    elif args.copy:
        return rdep.copy_packages(packages, args.copy)
    elif args.list:
        return rdep.list_packages()
    else:
        return rdep.sync_packages(packages, args.force)

if __name__ == "__main__":
    if not main():
        exit(1)
