#!/usr/bin/env python

import argparse
import os
import time
import configparser
import subprocess

from platform_detection import *

ROOT_CONFIG_NAME = ".rdep"
PACKAGE_CONFIG_NAME = ".rdpack"
ANY_KEYWORD = "any"
RSYNC = "rsync"

def find_root(file_name):
    path = os.path.abspath(os.getcwd())

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
        path = splitpath(os.path.relpath(os.getcwd(), root))

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

def get_package_timestamp(path):
    file = os.path.join(path, PACKAGE_CONFIG_NAME)
    if not os.path.isfile(file):
        return None

    config = configparser.ConfigParser()
    config.read(file)
    return config["General"]["time"]

def update_package_timestamp(path):
    file_name = os.path.join(path, PACKAGE_CONFIG_NAME)

    config = configparser.ConfigParser()
    config.read(file_name)

    config["General"] = { "time": int(time.time()) }

    with open(file_name, "w") as file:
        config.write(file)

def sync_url(config_file):
    if not os.path.isfile(config_file):
        return None

    config = configparser.ConfigParser()
    config.read(config_file)
    return config["General"]["url"]

SYNC_NOT_FOUND = 0
SYNC_FAILED = 1
SYNC_SUCCESS = 2

def try_sync(root, url, prefix, package, force):
    src = os.path.join(url, prefix, package)
    dst = os.path.join(root, prefix, package)

    if not os.path.isdir(dst):
        os.makedirs(dst)

    command = [ RSYNC, "--archive", "--delete", "--relative"]

    time = get_package_timestamp(dst)
    newtime = None

    config_sync_command = command.copy()
    config_sync_command.append(os.path.join(src, PACKAGE_CONFIG_NAME))
    config_sync_command.append(dst)
    ret = subprocess.call(config_sync_command)
    if ret != 0:
        return SYNC_NOT_FOUND

    newtime = get_package_timestamp(dst)

    if not newtime:
        return SYNC_NOT_FOUND

    if time == newtime and not force:
        print("Package %s is up to date." % package)
        return SYNC_SUCCESS

    command.append(src + os.sep)
    command.append(dst)
    ret = subprocess.call(command)
    if ret != 0:
        print("Could not sync %s" % package)
        return SYNC_FAILED

    print("Done %s" % package)
    return SYNC_SUCCESS

def debug_prefix(prefix, debug):
    if not debug:
        return prefix
    return os.path.join(prefix, "debug")

def sync_package(root, url, prefix, package, debug, force):
    print("Synching %s..." % package)

    ret = try_sync(root, url, debug_prefix(prefix, debug), package, force)
    if ret == SYNC_NOT_FOUND:
        ret = try_sync(root, url, prefix, package, force)

    if ret == SYNC_NOT_FOUND:
        # TODO: implement iteration through variants
        any_prefix = "any/any/any"

        ret = try_sync(root, url, debug_prefix(any_prefix, debug), package, force)
        if ret == SYNC_NOT_FOUND:
            ret = try_sync(root, url, any_prefix, package, force)

    if ret == SYNC_NOT_FOUND:
        print("Could not find %s" % package)
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
    print("Uploading %s..." % package)

    remote = os.path.join(url, prefix, package)
    local = os.path.join(root, prefix, package)

    update_package_timestamp(local)

    command = [ RSYNC, "--archive", "--delete" ]
    command.append(local + os.sep)
    command.append(remote)

    ret = subprocess.call(command)
    if ret != 0:
        print("Could not upload %s" % package)
        return False

    print("Done %s" % package)
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

    any_prefix = "any/any/any"

    if debug:
        path = os.path.join(root, debug_prefix(any_prefix, debug), package)
        if os.path.exists(package_config_path(path)):
            return path

    path = os.path.join(root, any_prefix, package)
    if os.path.exists(package_config_path(path)):
        return path

    return None

def main():
    platform, arch, box, debug, package = detect_settings()

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--platform", type=str, help="Platform name.", default="")
    parser.add_argument("-a", "--arch", type=str, help="Architecture name.", default="")
    parser.add_argument("-b", "--box", type=str, help="Box name.", default="")
    parser.add_argument("-d", "--debug", dest="debug", help="Sync debug version.", action="store_true")
    parser.add_argument("-f", "--force", dest="force", help="Force sync.", action="store_true")
    parser.add_argument("-u", "--upload", dest="upload", help="Upload package to the repository.", action="store_true")
    parser.add_argument("--print-path", dest="print_path", help="Print package dir and exit.", action="store_true")
    parser.add_argument("packages", nargs='*', help="Packages to sync.", default="")

    args = parser.parse_args()

    if args.platform:
        platform = args.platform
    if not platform:
        platform = detect_platform()
    if not platform in supported_platforms and platform != ANY_KEYWORD:
        print("Unsupported platform " + platform)
        exit(1)

    if args.arch:
        arch = args.arch
    if not arch:
        arch = detect_arch()
    if not arch in supported_arches and arch != ANY_KEYWORD:
        print("Unsupported arch " + arch)
        exit(1)

    if args.box:
        box = args.box
    if not box:
        box = "default"
    if not box in supported_boxes and box != ANY_KEYWORD:
        print("Unsupported box " + box)
        exit(1)

    if args.debug:
        debug = args.debug

    packages = args.packages
    if not packages:
        if package:
            packages = [ os.path.basename(package) ]

    root = find_root(ROOT_CONFIG_NAME)
    prefix = os.path.join(platform, arch, box)

    if not root:
        root = os.getenv("NX_REPOSITORY", "")
    if not root:
        print("Package repository is not defined.")
        exit(1)

    if args.print_path:
        if not packages:
            exit(1)

        if len(packages) != 1:
            exit(1)

        path = locate_package(root, prefix, packages[0], args.debug)

        if not path:
            exit(1)

        print(path)
        exit(0)

    url = sync_url(os.path.join(root, ROOT_CONFIG_NAME))

    if args.upload:
        if not packages:
            print("No packages to upload")
            exit(1)

        if not upload_packages(root, url, prefix, packages, args.debug):
            exit(1)

    else:
        if not packages:
            print("No packages to sync")
            exit(0)

        if not sync_packages(root, url, prefix, packages, args.debug, args.force):
            exit(1)

if __name__ == "__main__":
    main()
