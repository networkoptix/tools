#!/usr/bin/env python3


import os
import configparser
import argparse


MAX_RECURSE_LEVEL = 3
RDPACK_FILE = ".rdpack"


def get_packages(root_dir: str):
    def get_packages_list_recursive(root_dir: str, subdir: str, recurse_level: int):
        if recurse_level == 0:
            return None

        subdirs = []

        for entry in os.listdir(os.path.join(root_dir, subdir)):
            entry_path = os.path.join(root_dir, subdir, entry)
            if os.path.isdir(entry_path):
                subdirs.append(entry)
            elif os.path.isfile(entry_path) and entry == RDPACK_FILE:
                yield subdir

        for sd in subdirs:
            for package in get_packages_list_recursive(
                    root_dir, os.path.join(subdir, sd), recurse_level - 1):
                yield package

    for package in get_packages_list_recursive(root_dir, "", MAX_RECURSE_LEVEL):
        yield package


def get_package_timestamp(package_dir: str):
    try:
        config = configparser.ConfigParser()
        config.read(os.path.join(package_dir, RDPACK_FILE))
        return config['General']['time']
    except:
        return None


def dump_timestamps(root_dir: str, timestamps_file: str):
    config = configparser.ConfigParser()
    config.add_section('Timestamps')
    for package in get_packages(root_dir):
        ts = get_package_timestamp(os.path.join(root_dir, package))
        if not ts is None:
            config['Timestamps'][package] = ts

    with open(timestamps_file, "w") as file:
        config.write(file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, help="RDep repository root")

    args = parser.parse_args()

    if args.root:
        root_dir = args.root
    else:
        root_dir = os.getcwd()

    dump_timestamps(root_dir, os.path.join(root_dir, "timestamps.dat"))


if __name__ == "__main__":
    main()
