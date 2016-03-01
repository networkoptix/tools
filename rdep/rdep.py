#!/usr/bin/env python

import argparse
import os
import time
import ConfigParser
import subprocess
import shutil
import tempfile

from platform_detection import *

ROOT_CONFIG_NAME = ".rdep"
PACKAGE_CONFIG_NAME = ".rdpack"
ANY_KEYWORD = "any"
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

def splitpath(path):
    if not path:
        return []

    d, f = os.path.split(path)
    return splitpath(d) + [f]

def detect_settings():
    platform = None
    arch = None
    box = None
    debug = False
    package = None

    root = find_root(ROOT_CONFIG_NAME)

    if root:
        path = splitpath(os.path.relpath(script_dir, root))

        if path:
            platform = path[0]
            path = path[1:]

        if path:
            arch = path[0]
            path = path[1:]

        if path:
            box = path[0]
            path = path[1:]

        if path:
            if path[0] == "debug":
                debug = True
                path = path[1:]

        if path:
            package = path[0]
            path = path[1:]

    return platform, arch, box, debug, package

def get_timestamp_from_package_config(file_name):
    if not os.path.isfile(file_name):
        return None

    config = ConfigParser.ConfigParser()
    config.read(file_name)
    return config.get("General", "time")

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

def sync_url(config_file):
    if not os.path.isfile(config_file):
        return None

    config = ConfigParser.ConfigParser()
    config.read(config_file)
    return config.get("General", "url")

SYNC_NOT_FOUND = 0
SYNC_FAILED = 1
SYNC_SUCCESS = 2

def remote_path(path):
    return path.replace(os.sep, '/')

def local_path(path):
    return os.path.relpath(path, os.getcwd())

def fetch_package_timestamp(url):
    file_name = tempfile.mktemp()
    command = list(RSYNC)
    command.append(url)
    command.append(file_name)

    verbose_rsync(command)

    timestamp = None

    with open(os.devnull, "w") as fnull:
        if subprocess.call(command, stderr = fnull) == 0:
            timestamp = get_timestamp_from_package_config(file_name)

    if os.path.isfile(file_name):
        os.remove(file_name)

    return timestamp

def try_sync(root, url, prefix, package, force):
    src = remote_path(os.path.join(url, prefix, package))
    dst = local_path(os.path.join(root, prefix, package))
    config_src = src + "/" + PACKAGE_CONFIG_NAME

    verbose_message("root {0}\nurl {1}\nprefix {2}\npackage {3}\nsrc {4}\ndst {5}".format(root, url, prefix, package, src, dst))

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
    command.append(remote_path(src) + "/")
    command.append(dst)

    verbose_rsync(command)

    if subprocess.call(command) != 0:
        print "Could not sync {0}".format(package)
        return SYNC_FAILED

    update_package_timestamp(dst, newtime)

    print "Done {0}".format(package)
    return SYNC_SUCCESS

def debug_prefix(prefix, debug):
    if not debug:
        return prefix
    return os.path.join(prefix, "debug")

def sync_package(root, url, prefix, package, debug, force):
    print "Synching {0}...".format(package)

    ret = SYNC_NOT_FOUND
    if debug:
        ret = try_sync(root, url, debug_prefix(prefix, debug), package, force)
    if ret == SYNC_NOT_FOUND:
        ret = try_sync(root, url, prefix, package, force)

    if ret == SYNC_NOT_FOUND:
        # TODO: implement iteration through variants
        any_prefix = ANY_KEYWORD

        if debug:
            ret = try_sync(root, url, debug_prefix(any_prefix, debug), package, force)
        if ret == SYNC_NOT_FOUND:
            ret = try_sync(root, url, any_prefix, package, force)

    if ret == SYNC_NOT_FOUND:
        print "Could not find {0}".format(package)
        return False

    if ret == SYNC_FAILED:
        return False

    return True

def sync_packages(root, url, prefix, packages, debug, force):
    success = True

    for package in packages:
        success = success and sync_package(root, url, prefix, package, debug, force)

    return success

def upload_package(root, url, prefix, package):
    print "Uploading {0}...".format(package)

    remote = os.path.join(url, prefix, package)
    local = os.path.join(root, prefix, package)

    update_package_timestamp(local)

    command = list(RSYNC)
    command.append("--exclude")
    command.append(PACKAGE_CONFIG_NAME)
    command.append(local + os.sep)
    command.append(remote)

    if subprocess.call(command) != 0:
        print "Could not upload {0}".format(package)
        return False

    command = list(RSYNC)
    command.append(os.path.join(local, PACKAGE_CONFIG_NAME))
    command.append(remote)

    if subprocess.call(command) != 0:
        print "Could not upload {0}".format(package)
        return False

    print "Done {0}".format(package)
    return True

def upload_packages(root, url, prefix, packages, debug):
    success = True

    if debug:
        prefix = os.path.join(prefix, "debug")

    for package in packages:
        success = success and upload_package(root, url, prefix, package)

    return success

def package_config_path(path):
    return os.path.join(path, PACKAGE_CONFIG_NAME)

def locate_package(root, prefix, package, debug):
    if debug:
        path = os.path.join(root, debug_prefix(prefix, debug), package)
        if os.path.exists(package_config_path(path)):
            return path

    path = os.path.join(root, prefix, package)
    if os.path.exists(package_config_path(path)):
        return path

    any_prefix = ANY_KEYWORD

    if debug:
        path = os.path.join(root, debug_prefix(any_prefix, debug), package)
        if os.path.exists(package_config_path(path)):
            return path

    path = os.path.join(root, any_prefix, package)
    if os.path.exists(package_config_path(path)):
        return path

    return None

def copy_packages(root, prefix, packages, debug, target_dir):
    for package in packages:
        print "Copying package {0} into {1}".format(package, target_dir)
        path = locate_package(root, prefix, package, debug)
        if not path:
            print "Could not locate {0}".format(package)
            exit(1)

        for dirname, dirnames, filenames in os.walk(path):
            rel_dir = os.path.relpath(dirname, path)
            dir = os.path.abspath(os.path.join(target_dir, rel_dir))
            if not os.path.isdir(dir):
                os.makedirs(dir)
            for filename in filenames:
                entry = os.path.join(dirname, filename)
                shutil.copy(entry, dir)

def get_prefix(platform, arch, box):
    return os.path.join(platform, arch, box) if arch == 'arm' else os.path.join(platform, arch)

def get_repository_root():
    root = find_root(ROOT_CONFIG_NAME)
    #if not root:
        #root = os.getenv("NX_REPOSITORY", "")
    if not root:
        root = os.path.join(script_dir, 'packages')
    return root

def fetch_packages(packages, platform, arch, box, debug = False, verbose_messages = False):
    if verbose_messages:
        global verbose
        verbose = True

    if not platform in supported_platforms and platform != ANY_KEYWORD:
        print "Unsupported platform {0}".format(platform)
        return False

    if not arch in supported_arches and arch != ANY_KEYWORD:
        print "Unsupported arch {0}".format(arch)
        return False

    if not box in supported_boxes and box != ANY_KEYWORD:
        print "Unsupported box {0}".format(box)
        return False

#    if not packages:
#        if package:
#            packages = [ os.path.basename(package) ]

    prefix = get_prefix(platform, arch, box)
    print "Ready to work on {0}".format(prefix)

    root = get_repository_root()
    print "Repository root dir: {0}".format(root)

    url = sync_url(os.path.join(root, ROOT_CONFIG_NAME))

    if not packages:
        print "No packages to sync"
        return True

    #args.force
    if not sync_packages(root, url, prefix, packages, debug, False):
        return False

    return True
#    if args.copy_to:
#        copy_packages(root, prefix, packages, debug, args.copy_to)

def main():
    #platform, arch, box, debug, package = detect_settings()

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--platform",     help="Platform name.",      default=detect_platform())
    parser.add_argument("-a", "--arch",         help="Architecture name.",  default=detect_arch())
    parser.add_argument("-b", "--box",          help="Box name.",           default="none")
    parser.add_argument("-d", "--debug",        help="Sync debug version.",                 action="store_true")
    parser.add_argument("-f", "--force",        help="Force sync.",                         action="store_true")
    parser.add_argument("-u", "--upload",       help="Upload package to the repository.",   action="store_true")
    parser.add_argument("-v", "--verbose",      help="Additional debug output.",            action="store_true")
    parser.add_argument("--print-path",         help="Print package dir and exit.",         action="store_true")
    parser.add_argument("packages", nargs='*',  help="Packages to sync.",   default="")

    args = parser.parse_args()

    if args.print_path:
        if not packages:
            exit(1)

        if len(packages) != 1:
            exit(1)

        prefix = get_prefix(platform, arch, box)
        root = get_repository_root()

        path = locate_package(root, prefix, packages[0], debug)

        if not path:
            exit(1)

        print path
        exit(0)

    if args.upload:
        if not packages:
            print "No packages to upload"
            exit(1)

        prefix = get_prefix(platform, arch, box)
        root = get_repository_root()
        if not upload_packages(root, url, prefix, packages, args.debug):
            exit(1)
        print "Uploaded successfully"
        exit(0)

    if not fetch_packages(args.packages, args.platform, args.arch, args.box, args.debug, args.verbose):
        exit(1)


if __name__ == "__main__":
    main()
