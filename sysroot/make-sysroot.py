#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import subprocess
import shutil
import re

class SysrootConfig:
    def __init__(self):
        self.sysroot_dir = None
        self.force_remove = False
        self.packages = []
        self.arch_prefix = None

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
    except KeyError:
        pass

    return config

def check_packages(packages: list):
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
        print("Please install them using the following command:")
        print("apt install " + " ".join(missing_packages))
        sys.exit(1)

def get_package_files_list(package: str):
    p = subprocess.Popen(["dpkg-query", "-L", package], stdout=subprocess.PIPE)
    result = p.communicate()
    if result[1]:
        sys.exit("Cannot list files for package {}.".format(package))
    
    return result[0].decode("utf-8").split(sep='\n')

def copy_file(src: str, dst: str):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copyfile(src, dst)
    except:
        sys.exit("Cannot copy {} to {}".format(src, dst))

def create_symlinks(lib_path: str, additional_symlink: str = ""):
    path, base_name = os.path.split(lib_path)

    splitted = base_name.split(".so.")
    if len(splitted) != 2:
        return

    if additional_symlink:
        additional_symlink = os.path.join(path, os.path.basename(additional_symlink))

    short_name = os.path.join(path, splitted[0] + ".so")
    if os.path.isfile(short_name):
        os.remove(short_name)
    os.symlink(base_name, short_name)
    if additional_symlink == short_name:
        additional_symlink = ""

    version_suffix = splitted[1]
    splitted = version_suffix.split(".", maxsplit=1)
    if len(splitted) == 2:
        medium_name = short_name + "." + splitted[0]
        if os.path.isfile(medium_name):
            os.remove(medium_name)
        os.symlink(base_name, medium_name)
        if additional_symlink == medium_name:
            additional_symlink = ""

    if additional_symlink:
        if os.path.isfile(additional_symlink):
            os.remove(additional_symlink)
        os.symlink(base_name, additional_symlink)

def copy_library(src: str, dst: str):
    if os.path.islink(src):
        lib = os.readlink(src)
        lib_path = lib
        if not lib.startswith("/"):
            lib_path = os.path.join(os.path.dirname(src), lib)
        if not os.path.exists(lib_path):
            print("{} points to inexistent file {}".format(src, lib))
            return

        dst = os.path.join(os.path.dirname(dst), os.path.basename(lib))
        copy_file(lib_path, dst)
        create_symlinks(dst, additional_symlink=src)
    elif os.path.isfile(src):
        copy_file(src, dst)
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
            copy_file(file, config.sysroot_dir + file)
        elif file.endswith(".so"):
            if file.startswith("/usr/lib/"):
                copy_library(file, config.sysroot_dir + file)
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
                    copy_file(file, dst)
                continue

            copy_file(file, config.sysroot_dir + file)

def make_sysroot(config: SysrootConfig):
    if not config.packages:
        sys.exit("No packages specified in the config.")

    check_packages(config.packages)

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
    parser.add_argument("-c", "--config", type=str, required=True, help="Config file name.")
    parser.add_argument("-o", "--output-dir", type=str, required=True, help="Output directory.")
    parser.add_argument("-f", "--force-remove", action="store_true",
        help="Remove sysroot directory if it already exists.")
    args = parser.parse_args()

    config = read_config(args.config)
    config.sysroot_dir = args.output_dir
    config.force_remove = args.force_remove
    make_sysroot(config)
    validate_pkg_config(config)

if __name__ == "__main__":
    main()
