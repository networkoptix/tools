#!/bin/python

import argparse
import logging
import re
import sys
import tarfile
import zipfile

from pathlib import Path

try:
    from artifactory import ArtifactoryPath
except ModuleNotFoundError:
    print("Artifactory integration module not found. Run\npip install dohq-artifactory")
    sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO)

ARTIFACTORY_URL = ArtifactoryPath(
    'https://artifactory.us.nxteam.dev/artifactory/release-vms')
ARTIFACTORY_CONAN_URL = ArtifactoryPath(
    'http://artifactory.ru.nxteam.dev/artifactory/conan-local-prod/_')
RELEASE_DIR = 'windows'

CLIENT_FILENAMES = {
    'client_update',
    'client_debug',
    'libs_debug',
}


def find_full_version(build: int, customization: str):
    logger.info(f"Trying to find version for build {build} in {customization}")
    for path in ARTIFACTORY_URL / customization:
        if str(build) in path.stem:
            full_version = path.stem
            logger.info(f"Version {full_version} found")
            return full_version
    return None


def enum_urls(dist_dir: ArtifactoryPath):
    for path in dist_dir:
        parts = path.stem.split('-')  # nxwitness-client_debug-5.2.0.35169-windows_x64-private-prod
        if len(parts) < 4:
            logger.error(f"Invalid artifactory path {path}")
            continue  # Not properly-formed name.
        app_type = parts[1]  # client_debug
        platform = parts[3]  # windows_x64
        if app_type in CLIENT_FILENAMES and platform.startswith('win'):
            yield path

    release_dir = dist_dir / RELEASE_DIR
    if release_dir.exists():
        yield from enum_urls(release_dir)


def download_file(url: ArtifactoryPath, target_path: Path) -> Path:
    if target_path.exists():
        logger.debug('Already downloaded: %s' % target_path)
        return
    logger.info('Download: %s -> %s' % (url, target_path))
    url.writeto(out=target_path, chunk_size=102400, progress_func=None)


def extract_file(filename: Path, directory: Path):
    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(directory)


def download_conan_artifact(conan_refs: Path, artifact_name: str, downloads_directory: Path):
    match = None
    conan_artifact_pattern = re.compile(
        f"{artifact_name}/(?P<version>.*?)#(?P<recipe_rev>[0-9A-Fa-f]+):(?P<package_id>[0-9A-Fa-f]+)#(?P<package_rev>[0-9A-Fa-f]+)")

    with open(conan_refs) as file:
        for line in file:
            match = conan_artifact_pattern.match(line)
            if match:
                logger.info(f"Detected {artifact_name} version {line[:-1]}")
                break

    if not match:
        logger.error(f"Cannot find artifact {artifact_name} in file {conan_refs.as_posix()}")
        return

    version = match.group('version')
    recipe_rev = match.group('recipe_rev')
    package_id = match.group('package_id')
    package_rev = match.group('package_rev')
    artifact_path = ARTIFACTORY_CONAN_URL / artifact_name / version / '_' / recipe_rev / 'package' / package_id / package_rev / 'conan_package.tgz'
    if not artifact_path.exists():
        logger.error(f"Cannot find artifact {artifact_path}")
        return

    target_filename = downloads_directory / artifact_name / version / recipe_rev/ package_id / package_rev / artifact_path.name
    if target_filename.exists():
        logger.info(f"File {target_filename.as_posix()} is already downloaded")
        return
    else:
        target_filename.parent.mkdir(parents=True, exist_ok=True)
        download_file(artifact_path, target_filename)

    target_folder = Path().resolve() / "conan" / f"{artifact_name}-{version}-{recipe_rev}-{package_rev}"
    target_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extracting {artifact_name}...")
    with tarfile.open(target_filename) as tf:
        tf.extractall(target_folder)


def download_build(build, customization, version, force, with_qt):
    downloads_directory = Path().resolve() / 'downloads'
    downloads_directory.mkdir(exist_ok=True)

    full_version = f'{version}.0.{build}' if version else find_full_version(build, customization)
    if not full_version:
        logger.info(f"Cannot find any version for build {build}")
        return

    dist_dir = ARTIFACTORY_URL / customization / full_version
    if not dist_dir.exists():
        logger.info(f"Version {full_version} is not published")
        return

    target_directory = Path().resolve() / f'{full_version}-{customization}'
    try:
        target_directory.mkdir(exist_ok=force)
        for url in enum_urls(dist_dir):
            target_filename = downloads_directory / url.name
            logger.info(f"Downloading {url} into {target_filename}")
            download_file(url, target_filename)
            logger.info(f"Extracting {target_filename} into {target_directory}")
            extract_file(target_filename, target_directory)
    except FileExistsError:
        logger.info(f"Version {target_directory} is already downloaded")

    if with_qt:
        conan_refs = target_directory / 'conan_refs.txt'
        if conan_refs.exists():
            logger.info(f"Downloading Qt")
            download_conan_artifact(conan_refs, "qt", downloads_directory)
        else:
            logger.warning(f"{conan_refs.as_posix()} file not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build', type=int, help="Build number")
    parser.add_argument('-c', '--customization', help="Customization", default='default')
    parser.add_argument('-v', '--version', help="Release version")
    parser.add_argument('-f', '--force', help="Force re-download", action='store_true')
    parser.add_argument('--with-qt', help="Download Qt binaries", action='store_true')
    args = parser.parse_args()
    download_build(args.build, args.customization, args.version, args.force, args.with_qt)


if __name__ == "__main__":
    main()
