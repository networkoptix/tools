#!/bin/python

import argparse
import logging
import zipfile

from pathlib import Path
from artifactory import ArtifactoryPath

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(message)s',
    level=logging.INFO)

ARTIFACTORY_URL = ArtifactoryPath(
    'https://artifactory.ru.nxteam.dev/artifactory/release-vms')
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


def download_file(url: ArtifactoryPath, target_path: Path) -> Path:
    if target_path.exists():
        logger.debug('Already downloaded: %s' % target_path)
        return
    logger.info('Download: %s -> %s' % (url, target_path))
    url.writeto(out=target_path, chunk_size=102400, progress_func=None)


def extract_file(filename: Path, directory: Path):
    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(directory)


def download_build(build, customization, version, force):
    downloads_directory = Path().resolve() / 'downloads'
    downloads_directory.mkdir(exist_ok=True)

    full_version = f'{version}.0.{build}' if version else find_full_version(build, customization)
    if not full_version:
        logger.info(f"Cannot find any version for build {build}")
        return

    dist_dir = ARTIFACTORY_URL / customization / full_version / RELEASE_DIR
    if not dist_dir.exists():
        logger.info(f"Version {full_version} is not published")
        return

    target_directory = Path().resolve() / f'{full_version}-{customization}'
    try:
        target_directory.mkdir(exist_ok=force)
    except FileExistsError:
        logger.info(f"Version {target_directory} is already downloaded")
        return

    for url in enum_urls(dist_dir):
        target_filename = downloads_directory / url.name
        logger.info(f"Downloading {url} into {target_filename}")
        download_file(url, target_filename)
        logger.info(f"Extracting {target_filename} into {target_directory}")
        extract_file(target_filename, target_directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build', type=int, help="Build number")
    parser.add_argument('-c', '--customization', help="Customization", default='default')
    parser.add_argument('-v', '--version', help="Release version")
    parser.add_argument('-f', '--force', help="Force re-download", action='store_true')
    args = parser.parse_args()
    download_build(args.build, args.customization, args.version, args.force)


if __name__ == "__main__":
    main()
