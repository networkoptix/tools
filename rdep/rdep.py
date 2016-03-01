#!/usr/bin/env python

import argparse
import os
import time
import ConfigParser
import subprocess
import shutil
import tempfile
import posixpath

from platform_detection import *

ROOT_CONFIG_NAME = ".rdep"
PACKAGE_CONFIG_NAME = ".rdpack"
ANY_KEYWORD = "any"
DEBUG_SUFFIX = "-debug"
RSYNC = [ "rsync", "--archive", "--delete" ]
if detect_platform() == "windows":
    RSYNC.append("--chmod=ugo=rwx")

verbose = False

script_dir = os.path.dirname(os.path.abspath(__file__))

def verbose_message(message):
    if verbose:
        print message

def verbose_rsync(command):
    verbose_message("Executing rsync:\n{0}".format(" ".join(command)))

def find_root(file_name):
    path = script_dir

    while not os.path.isfile(os.path.join(path, file_name)):
        nextpath = os.path.dirname(path)
        if path == nextpath:
            return None
        else:
            path = nextpath

    return path

def get_repository_root():
    root = find_root(ROOT_CONFIG_NAME)
    if not root:
        root = os.getenv("NX_REPOSITORY", "")
    if not root:
        root = os.path.join(script_dir, 'packages')
    return root

def get_sync_url(config_file):
    if not os.path.isfile(config_file):
        return None

    config = ConfigParser.ConfigParser()
    config.read(config_file)
    if not config.has_option("General", "url"):
        return None

    return config.get("General", "url")

def detect_repository():
    root = get_repository_root()
    if not root:
        print "Could not find repository root"
        exit(1)

    url = get_sync_url(os.path.join(root, ROOT_CONFIG_NAME))
    if not url:
        print "Could not find sync url for {0}".format(root)
        exit(1)

    return root, url

def get_timestamp_from_package_config(file_name):
    if not os.path.isfile(file_name):
        return None

    config = ConfigParser.ConfigParser()
    config.read(file_name)

    if not config.has_option("General", "time"):
        return None

    return config.getint("General", "time")

def get_package_timestamp(path):
    return get_timestamp_from_package_config(os.path.join(path, PACKAGE_CONFIG_NAME))

def update_package_timestamp(path, timestamp = None):
    file_name = os.path.join(path, PACKAGE_CONFIG_NAME)

    if timestamp == None:
        timestamp = time.time()

    config = ConfigParser.ConfigParser()
    config.read(file_name)

    if not config.has_section("General"):
        config.add_section("General")

    config.set("General", "time", int(timestamp))

    with open(file_name, "w") as file:
        config.write(file)

SYNC_NOT_FOUND = 0
SYNC_FAILED = 1
SYNC_SUCCESS = 2

# Workaround against rsync bug: all paths with semicolon are counted as remote, so 'rsync rsync://server/path c:\test\path' won't work on windows
def posix_path(path):
    if len(path) > 1 and path[1] == ':':
        drive_letter = path[0].lower()
        return "/cygdrive/{0}{1}".format(drive_letter, path[2:].replace("\\", "/"))

    return path

def fetch_package_timestamp(url):
    file_name = tempfile.mktemp()
    command = list(RSYNC)
    command.append(url)
    command.append(posix_path(file_name))

    verbose_rsync(command)

    timestamp = None

    with open(os.devnull, "w") as fnull:
        if subprocess.call(command, stderr = fnull) == 0:
            timestamp = get_timestamp_from_package_config(file_name)

    if os.path.isfile(file_name):
        os.remove(file_name)

    return timestamp

def try_sync(root, url, target, package, force):
    src = posixpath.join(url, target, package)
    dst = os.path.join(root, target, package)
    config_src = posixpath.join(src, PACKAGE_CONFIG_NAME)

    verbose_message("root {0}\nurl {1}\ntarget {2}\npackage {3}\nsrc {4}\ndst {5}".format(root, url, target, package, src, dst))

    newtime = fetch_package_timestamp(config_src)
    if newtime == None:
        return SYNC_NOT_FOUND

    time = get_package_timestamp(dst)
    if newtime == time and not force:
        return SYNC_SUCCESS

    if not os.path.isdir(dst):
        os.makedirs(dst)

    command = list(RSYNC)
    command.append("--exclude")
    command.append(PACKAGE_CONFIG_NAME)
    command.append(src + "/")
    command.append(posix_path(dst))

    verbose_rsync(command)

    if subprocess.call(command) != 0:
        print "Could not sync {0}".format(package)
        return SYNC_FAILED

    update_package_timestamp(dst, newtime)

    print "Done {0}".format(package)
    return SYNC_SUCCESS

def sync_package(root, url, target, package, debug, force):
    print "Synching {0}...".format(package)

    ret = SYNC_NOT_FOUND
    if debug:
        ret = try_sync(root, url, target, package + DEBUG_SUFFIX, force)
    if ret == SYNC_NOT_FOUND:
        ret = try_sync(root, url, target, package, force)

    if ret == SYNC_NOT_FOUND:
        any_target = ANY_KEYWORD

        if debug:
            ret = try_sync(root, url, any_target, package + DEBUG_SUFFIX, force)
        if ret == SYNC_NOT_FOUND:
            ret = try_sync(root, url, any_target, package, force)

    if ret == SYNC_NOT_FOUND:
        print "Could not find {0}".format(package)
        return False

    if ret == SYNC_FAILED:
        return False

    return True

def sync_packages(root, url, target, packages, debug, force):
    success = True

    for package in packages:
        if not sync_package(root, url, target, package, debug, force):
            success = False

    return success

def upload_package(root, url, target, package):
    print "Uploading {0}...".format(package)

    remote = posixpath.join(url, target, package)
    local = os.path.join(root, target, package)

    update_package_timestamp(local)

    command = list(RSYNC)
    command.append("--exclude")
    command.append(PACKAGE_CONFIG_NAME)
    command.append(posix_path(local) + "/")
    command.append(remote)

    if subprocess.call(command) != 0:
        print "Could not upload {0}".format(package)
        return False

    command = list(RSYNC)
    command.append(posix_path(os.path.join(local, PACKAGE_CONFIG_NAME)))
    command.append(remote)

    if subprocess.call(command) != 0:
        print "Could not upload {0}".format(package)
        return False

    print "Done {0}".format(package)
    return True

def upload_packages(target, packages, debug = False):
    root, url = detect_repository()

    success = True

    if not packages:
        print "No packages to upload"
        exit(1)

    for package in packages:
        package_name = package + DEBUG_SUFFIX if debug else package
        if not upload_package(root, url, target, package_name):
            success = False

    print "Uploaded successfully"
    exit(0 if success else 1)

def package_config_path(path):
    return os.path.join(path, PACKAGE_CONFIG_NAME)

def locate_package(target, package, debug = False):
    root, _ = detect_repository()

    if debug:
        path = os.path.join(root, target, package + DEBUG_SUFFIX)
        if os.path.exists(package_config_path(path)):
            return path

    path = os.path.join(root, target, package)
    if os.path.exists(package_config_path(path)):
        return path

    any_target = ANY_KEYWORD

    if debug:
        path = os.path.join(root, any_target, package + DEBUG_SUFFIX)
        if os.path.exists(package_config_path(path)):
            return path

    path = os.path.join(root, any_target, package)
    if os.path.exists(package_config_path(path)):
        return path

    return None

def fetch_packages(target, packages, debug = False, force = False):
    root, url = detect_repository()

    print "Ready to work on {0}".format(target)
    print "Repository root dir: {0}".format(root)

    if not packages:
        print "No packages to sync"
        exit(1)

    if not sync_packages(root, url, target, packages, debug, force):
        exit(1)

    exit(0)

def print_path(target, packages, debug):
    if not packages or len(packages) != 1:
        exit(1)

    path = locate_package(target, packages[0], debug)
    if not path:
        exit(1)
    print(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target",       help="Target classifier.",  default=detect_target())
    parser.add_argument("-d", "--debug",        help="Sync debug version.",                 action="store_true")
    parser.add_argument("-f", "--force",        help="Force sync.",                         action="store_true")
    parser.add_argument("-u", "--upload",       help="Upload package to the repository.",   action="store_true")
    parser.add_argument("-v", "--verbose",      help="Additional debug output.",            action="store_true")
    parser.add_argument("--print-path",         help="Print package dir and exit.",         action="store_true")
    parser.add_argument("packages", nargs='*',  help="Packages to sync.",   default="")

    args = parser.parse_args()

    target = args.target
    if not target in supported_targets and target != ANY_KEYWORD:
        print "Unsupported target {0}".format(target)
        print "Supported targets:\n{0}".format("\n".join(supported_targets))
        exit(1)

    packages = args.packages
    if not packages:
        path = find_root(PACKAGE_CONFIG_NAME)
        if path:
            package = os.path.basename(path)

            path = os.path.dirname(path)
            auto_target = os.path.basename(path)

            if detect_target in supported_targets and package:
                packages = [ package ]
                target = auto_target

    if args.verbose:
        global verbose
        verbose = True

    if args.print_path:
        print_path(target, packages, args.debug)
    elif args.upload:
        upload_packages(target, packages, args.debug)
    else:
        fetch_packages(target, packages, args.debug, args.force)

if __name__ == "__main__":
    main()
