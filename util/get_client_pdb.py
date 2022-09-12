#!/bin/python

import argparse
import os
import re
import requests
import zipfile

ROOT_URL = 'https://artifactory.ru.nxteam.dev/artifactory/build-vms-release/'
BRANCH_NAME_PATTERN = re.compile('<a href="(.*)/">')

CLIENT_FILENAMES = [
    'client_update',
    'client_debug',
    'libs_debug'
]

CHUNK_SIZE = 8192


def get_branch_list():
    r = requests.get(ROOT_URL)
    branches = sorted(BRANCH_NAME_PATTERN.findall(r.text), reverse=True)
    return branches


def detect_branch(build):
    for branch in get_branch_list():
        print(f"Checking branch {branch}")
        r = requests.get(f'{ROOT_URL}/{branch}/')
        pattern = f'<a href="({build})/">'
        if re.search(pattern, r.text) is not None:
            return branch
    return None


def download_file(file_url, output):
    r = requests.get(file_url)
    if r.status_code == 200:
        with open(output, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                fd.write(chunk)
        return 0
    return 1


def extract_file(filename, directory):
    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(directory)
    os.remove(filename)


def download_files(package_url, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    r = requests.get(package_url)
    for filename in CLIENT_FILENAMES:
        pattern = r'"([^"]*{}-[\.\d]*-win[\.\w-]*zip)'.format(filename)
        match = re.search(pattern, r.text)
        if not match:
            print("File {} could not be found".format(filename))
            return
        target_filename = match.group(1)
        file_url = package_url + target_filename
        print("Downloading {}".format(file_url))
        if download_file(file_url, target_filename) != 0:
            print("Download failed")
            return
        print("Extracting {}".format(file_url))
        extract_file(target_filename, target_directory)


def download_build(build, customization, branch=None):
    if not branch:
        branch = detect_branch(build)
        if branch:
            print("Branch {} was selected".format(branch))
    if not branch:
        print("Branch cannot be found")
        return

    package_url = f'{ROOT_URL}/{branch}/{build}/{customization}/windows-x64/distrib/'
    print(f"Downloading from {package_url}")
    target_directory = '{}-{}'.format(build, customization)
    download_files(package_url, target_directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build', type=int, help="Build number")
    parser.add_argument('-c', '--customization', help="Customization", default='default')
    parser.add_argument('-b', '--branch', help="Source branch")
    args = parser.parse_args()
    download_build(args.build, args.customization, args.branch)


if __name__ == "__main__":
    main()
