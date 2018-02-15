#!/usr/bin/env python3

import argparse
import configparser
import getpass
import os
import re
import shutil
import subprocess
import sys

class SysrootConfig:
    def __init__(self):
        self.arch_prefix = None
        self.auto_install = False
        self.force_remove = False
        self.packages = []
        self.recursive_symlinks = False
        self.sysroot_dir = None
        self.verbose = False

def read_config(config_file: str):
    parser = configparser.ConfigParser()
    parser.read(config_file)
    
    config = SysrootConfig()

    try:
        packages = parser["Sysroot"]["packages"]
        config.packages = packages.split()
    except KeyError:
        pass

    try:
        config.arch_prefix = parser["Sysroot"]["arch_prefix"]
        config.recursive_symlinks = parser["Sysroot"]["recursive_symlinks"]
    except KeyError:
        pass

    return config

def check_packages(packages: list, auto_install: bool):
    print("Checking packages...")

    p = subprocess.Popen(["dpkg-query", "-Wf=${package} "], stdout=subprocess.PIPE)
    result = p.communicate()
    if result[1]:
        sys.exit("Cannot retrieve a list of the installed packages.")

    installed_packages = set(result[0].decode("utf-8").split())

    missing_packages = []

    for package in packages:
        if package in installed_packages:
            print("[ OK ] {}".format(package))
        else:
            print("[FAIL] {}".format(package))
            missing_packages.append(package)

    if missing_packages:
        print("Some packages are not installed in the system.")
        command = "apt-get install " + " ".join(missing_packages)
        if getpass.getuser() != 'root':
            command = 'sudo ' + command
        if auto_install:
            if os.system(command) != 0:
                sys.exit("Unable to install required packages.")
            else:
                check_packages(packages, auto_install=False)
        else:
            print("Please install them using the following command:\n  " + command)
            sys.exit(1)

def get_package_files_list(package: str):
    p = subprocess.Popen(["dpkg-query", "-L", package], stdout=subprocess.PIPE)
    result = p.communicate()
    if result[1]:
        sys.exit("Cannot list files for package {}.".format(package))
    
    return result[0].decode("utf-8").split('\n') 

def copy_file(src: str, dst: str, verbose: bool):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copyfile(src, dst)
        if verbose: print("  copy {} -> {}".format(src, dst))
    except (IOError, OSError):
        sys.exit("Cannot copy {} to {}".format(src, dst))

def create_symlinks(lib_path: str, additional_symlink: str = "", verbose: bool = False):
    path, base_name = os.path.split(lib_path)

    splitted = base_name.split(".so.")
    if len(splitted) != 2:
        return

    if additional_symlink:
        additional_symlink = os.path.join(path, os.path.basename(additional_symlink))

    short_name = os.path.join(path, splitted[0] + ".so")
    if os.path.isfile(short_name):
        os.remove(short_name)
    if verbose: 
        print("  link {} -> {}".format(short_name, base_name))
    os.symlink(base_name, short_name)
    if additional_symlink == short_name:
        additional_symlink = ""

    version_suffix = splitted[1]
    splitted = version_suffix.split(".", 1)
    if len(splitted) == 2:
        medium_name = short_name + "." + splitted[0]
        if os.path.isfile(medium_name):
            os.remove(medium_name)
        if verbose: 
            print("  link {} -> {}".format(medium_name, base_name))
        os.symlink(base_name, medium_name)
        if additional_symlink == medium_name:
            additional_symlink = ""

    if additional_symlink:
        if os.path.isfile(additional_symlink):
            os.remove(additional_symlink)
        if verbose: 
            print("  link {} -> {}".format(additional_symlink, base_name))
        os.symlink(base_name, additional_symlink)

def copy_library(src: str, dst: str, config: SysrootConfig):
    if os.path.islink(src):
        lib = os.readlink(src)
        lib_path = lib
        if not lib.startswith("/"):
            lib_path = os.path.join(os.path.dirname(src), lib)
        if not os.path.exists(lib_path):
            print("{} points to inexistent file {}".format(src, lib))
            return

        real_dst = os.path.join(os.path.dirname(dst), os.path.basename(lib))
        if config.recursive_symlinks:
            copy_library(lib_path, real_dst, config)
            if not os.path.islink(dst):
                base_name = os.path.basename(real_dst)
                if config.verbose:
                    print("  link {} -> {}".format(dst, base_name))
                os.symlink(base_name, dst)
        else:
            copy_file(lib_path, real_dst, config.verbose)
        create_symlinks(real_dst, additional_symlink=src)

    elif os.path.isfile(src):
        copy_file(src, dst, config.verbose)
    else:
        print("{} is not a file".format(src))

def copy_files(package: str, config: SysrootConfig):
    files = get_package_files_list(package)
    for file in files:
        if os.path.isdir(file):
            continue

        if file.endswith(".h") or file.endswith(".hpp"):
            if file.startswith("/usr/share"):
                continue
            copy_file(file, config.sysroot_dir + file, config.verbose)
        elif file.endswith(".so") or (config.recursive_symlinks and ".so." in file):
            if file.startswith("/usr/lib/") or file.startswith("/lib/"):
                copy_library(file, config.sysroot_dir + file, config)
            else:
                print("Ignoring library in non-handled location: {}".format(file))
        elif file.endswith(".pc"):
            if file.startswith("/usr/share"):
                if not config.arch_prefix:
                    print("Non-standard pkg-config location {}".format(file))
                    print("Please specify Sysroot/arch_prefix parameter in the config file.")
                    sys.exit(1)
                else:
                    dst = os.path.join(config.sysroot_dir, "usr/lib", config.arch_prefix, 
                        "pkgconfig", os.path.basename(file))
                    copy_file(file, dst, config.verbose)
                continue

            copy_file(file, config.sysroot_dir + file, config.verbose)

def make_sysroot(config: SysrootConfig):
    if not config.packages:
        sys.exit("No packages specified in the config.")

    check_packages(config.packages, config.auto_install)

    print("Copying files...")

    config.sysroot_dir = os.path.normpath(config.sysroot_dir)
    if os.path.exists(config.sysroot_dir):
        if config.force_remove:
            try:
                shutil.rmtree(config.sysroot_dir)
            except:
                sys.exit("Cannot remove {}.".format(config.sysroot_dir))
        else:
            sys.exit("{} is already exists. Use -f to remove it anyway.".format(config.sysroot_dir))

    try:
        os.makedirs(config.sysroot_dir)
    except:
        sys.exit("Cannot create directory {}.".format(config.sysroot_dir))

    for package in config.packages:
        print(" -- {}".format(package))
        copy_files(package, config)

def validate_pkg_config(config: SysrootConfig):
    print("Validating pkg-config...")

    pkg_config_dir = None

    libs_dir = os.path.join(config.sysroot_dir, "usr/lib")
    for arch_dir in os.listdir(libs_dir):
        dir = os.path.join(libs_dir, arch_dir, "pkgconfig")
        if os.path.isdir(dir):
            pkg_config_dir = os.path.abspath(dir)
            break

    if not pkg_config_dir:
        sys.exit("pkgconfig dir is not found in sysroot.")

    print("pkg-config dir is {}".format(pkg_config_dir))

    os.environ["PKG_CONFIG_LIBDIR"] = pkg_config_dir

    for pc in os.listdir(pkg_config_dir):
        if not pc.endswith(".pc"):
            continue

        package = pc[:-3]
        result = subprocess.call(["pkg-config", "--exists", package])
        if result == 0:
            print("[ OK ] {}".format(package))
        else:
            print("[FAIL] {}".format(package))
            subprocess.call(["pkg-config", "--print-requires", "--print-requires-private", package])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auto-install", action="store_true", 
        help="Auto install missing packages.")
    parser.add_argument("-c", "--config", type=str, required=True, 
        help="Config file name.")
    parser.add_argument("-f", "--force-remove", action="store_true",
        help="Remove sysroot directory if it already exists.")
    parser.add_argument("-o", "--output-dir", type=str, required=True, 
        help="Output directory.")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Enable verbose output.")
    
    args = parser.parse_args()
    config = read_config(args.config)

    config.auto_install = args.auto_install
    config.force_remove = args.force_remove
    config.sysroot_dir = args.output_dir
    config.verbose = args.verbose

    if config.verbose:
        print("Options:")
        for option in vars(config).items():
            print("  {}: {}".format(*option))

    make_sysroot(config)
    validate_pkg_config(config)

if __name__ == "__main__":
    main()
