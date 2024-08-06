#!/usr/bin/env python

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import urlopen

SWAGGER_TEMPLATE_FILE_NAME = 'openapi_template.yaml'
APIDOCTOOL_PROPERTIES_FILE_NAME = 'apidoctool.properties'

ENV = os.environ.copy()

PACKAGE_REQUIREMENT_REGEX = re.compile(
    r'\b(?:build_|tool_)requires\(\s*\"(?P<package_name>[\w-]+?)\/'
    r'(?P<package_version>\d+\.\d+(?:\.\d+)?)\"\s+'
    r'\"\#(?P<recipe_id>\w{32})\"')
CONAN_PACKAGE_REF_REGEX = re.compile(r'[\w-]+\/\d+\.\d+(?:\.\d+)?\@(?:\#\w{32})?')


class ToolPaths:
    TOOL_DESCRIPTORS = {
        'swagger-codegen': {'attr_name': 'swagger', 'suffix': 'cli.jar'},
        'apidoctool': {'attr_name': 'apidoctool', 'suffix': 'apidoctool.jar'},
        'openjdk-jre': {'attr_name': 'java', 'suffix': 'bin/java'},
        'oasdiff': {'attr_name': 'oasdiff', 'suffix': 'bin/oasdiff'}
    }

    def __init__(self):
        self.java_path: Path
        self.apidoctool_path: Path
        self.swagger_path: Path
        self.oasdiff_path: Path

    def set_path_by_package_name(self, name: str, path: Path):
        if name not in self.TOOL_DESCRIPTORS:
            return
        descriptor = self.TOOL_DESCRIPTORS[name]
        setattr(self, f'{descriptor["attr_name"]}_path', path / descriptor['suffix'])


def _run_apidoctool(
        java_path: Path,
        apidoctool_path: Path,
        properties_file: Path,
        openapi_template_file: Path,
        source_dir: Path,
        output: Path)  -> subprocess.CompletedProcess:

    return subprocess.run([
        str(java_path),
        '-Dfile.encoding=UTF-8',
        '-jar',
        str(apidoctool_path),
        '-verbose',
        'code-to-json',
        '-openapi-template-json',
        openapi_template_file,
        '-output-openapi-json',
        output,
        '-config',
        properties_file,
        '-vms-path',
        str(source_dir)
    ])


def _run_swagger_codegen(
        java_path: Path,
        swagger_path: Path,
        template_file: Path,
        api_tmp_dir: Path) -> subprocess.CompletedProcess:

    return subprocess.run(
        [
            str(java_path),
            '-Dfile.encoding=UTF-8',
            '-jar',
            str(swagger_path),
            'generate',
            '--input-spec',
            str(template_file),
            '--lang',
            'openapi',
            '--output',
            str(api_tmp_dir),
            '--skip-overwrite',
             'true',
        ])


def _install_tools(
        source_dir: Path,
        repo_conanfile: Path,
        temp_dir: Path,
        forced_apidoctool_location: str) -> ToolPaths:
    artifactory_url = os.getenv('NX_ARTIFACTORY_URL', 'https://artifactory.nxvms.dev/artifactory/')
    conan_url = os.getenv('NX_CONAN_URL', f'{artifactory_url}/api/conan/conan')
    (conan_user, conan_password) = (
        os.getenv('NX_ARTIFACTORY_USERNAME'), os.getenv('NX_ARTIFACTORY_PASSWORD'))

    package_names = list(ToolPaths.TOOL_DESCRIPTORS.keys())
    if _is_conan_package_ref(forced_apidoctool_location):
        package_names = list(set(package_names) - {'apidoctool'})
    package_references = _extract_package_references(
        package_names=package_names, source_dir=source_dir, repo_conanfile=repo_conanfile)

    subprocess.run(['conan', 'remote', 'add', '-f', 'nx', conan_url], env=ENV)
    if conan_user and conan_password:
        subprocess.run(['conan', 'user', '-r', 'nx', conan_user, '-p', conan_password], env=ENV)

    if _is_conan_package_ref(forced_apidoctool_location):
        package_references.append(forced_apidoctool_location)

    for package_reference in package_references:
        subprocess.run(['conan', 'install', '-r', 'nx', package_reference], env=ENV)

    tool_paths = _get_tool_paths(package_references)
    if _is_url(forced_apidoctool_location):
        tool_paths.apidoctool_path = _download_apidoctool(
            url=forced_apidoctool_location, temp_dir=temp_dir)
    elif (not _is_conan_package_ref(forced_apidoctool_location)
          and forced_apidoctool_location is not None):
        # Assume forced_apidoctool_location is a path to a local file.
        tool_paths.apidoctool_path = Path(forced_apidoctool_location)

    return tool_paths


def _is_conan_package_ref(location: str) -> bool:
    return location and CONAN_PACKAGE_REF_REGEX.match(location)


def _is_url(location: str) -> bool:
    return location and (location.startswith('http://') or location.startswith('https://'))


def _download_apidoctool(url: str, temp_dir: Path) -> Path:
    apidoctool_path = temp_dir / ToolPaths.TOOL_DESCRIPTORS['apidoctool']['suffix']
    try:
        with urlopen(url) as response:
            content = response.read()
            with open(apidoctool_path, 'wb') as out_file:
                out_file.write(content)
    except Exception as e:
        raise RuntimeError(f"Can't download apidoctool from {url!r}: {e}")

    return apidoctool_path


def _extract_package_references(
        package_names: list, source_dir: Path, repo_conanfile: Path) -> list[str]:
    package_references = []
    with open(source_dir / repo_conanfile, 'r') as f:
        for line in f:
            if (result := PACKAGE_REQUIREMENT_REGEX.search(line)):
                package_name = result.group('package_name')
                if package_name in package_names:
                    package_version = result.group('package_version')
                    recipe_id = result.group('recipe_id')
                    package_references.append(f'{package_name}/{package_version}@#{recipe_id}')

    return package_references


def _get_tool_paths(package_references: list[str]) -> ToolPaths:
    result = ToolPaths()

    for package_reference in package_references:
        conan_info_args = ['conan', 'info', '--paths', '--only', 'package_folder']
        package_info = subprocess.run(
            conan_info_args + [package_reference], env=ENV, encoding='utf-8', capture_output=True)

        # Get paths for the package and its dependencies.
        package_name = ''
        for info_line in package_info.stdout.split('\n'):
            if not info_line:
                continue
            if 'package_folder' in info_line:
                _, __, package_path = info_line.partition(':')
                result.set_path_by_package_name(package_name, Path(package_path.strip()))
            else:
                package_name = info_line[:info_line.index('/')]

    return result


def generate_openapi_schemas(
        source_dir: Path,
        repo_conanfile: Path,
        output_dir: Path,
        packages_dir: Path = None,
        forced_apidoctool_location: str = None):
    temp_dir_object = tempfile.TemporaryDirectory()
    temp_dir = Path(temp_dir_object.name)

    swagger_output_dir = temp_dir / 'swagger_output'
    shutil.rmtree(swagger_output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in output_dir.glob('*'):
        f.unlink()

    if 'CONAN_USER_HOME' not in ENV:
        ENV['CONAN_USER_HOME'] = str(packages_dir if packages_dir else temp_dir / 'packages')
    ENV['CONAN_REVISIONS_ENABLED'] = '1'
    tool_paths = _install_tools(
        source_dir=source_dir,
        repo_conanfile=repo_conanfile,
        temp_dir=temp_dir,
        forced_apidoctool_location=forced_apidoctool_location)

    for properties_file in source_dir.glob(f'**/{APIDOCTOOL_PROPERTIES_FILE_NAME}'):
        _generate_openapi_schema(
            properties_file=properties_file,
            swagger_output_dir=swagger_output_dir,
            apidoctool_output_dir=output_dir,
            tool_paths=tool_paths,
            source_dir=source_dir)


def _generate_openapi_schema(
        properties_file: Path,
        swagger_output_dir: Path,
        apidoctool_output_dir: Path,
        tool_paths: ToolPaths,
        source_dir: Path):
    properties_dir = properties_file.parent
    template_file = properties_dir / SWAGGER_TEMPLATE_FILE_NAME
    if not template_file.exists():
        print(
            f'File {SWAGGER_TEMPLATE_FILE_NAME!r} not found in {str(properties_dir)!r}/; '
            'skipping.')

    api_tmp_dir_name = (
        f'{properties_dir.parents[1].name}-{properties_dir.parents[0].name}-{properties_dir.name}')
    api_tmp_dir = swagger_output_dir / api_tmp_dir_name
    api_tmp_dir.mkdir(parents=True)

    _run_swagger_codegen(
        java_path=tool_paths.java_path,
        swagger_path=tool_paths.swagger_path,
        template_file=template_file,
        api_tmp_dir=api_tmp_dir)

    output_file = apidoctool_output_dir / (
        f'{properties_dir.parents[0].name}-{properties_dir.name}.json')
    _run_apidoctool(
        java_path=tool_paths.java_path,
        apidoctool_path=tool_paths.apidoctool_path,
        openapi_template_file=api_tmp_dir / 'openapi.json',
        properties_file=properties_file,
        source_dir=source_dir,
        output=output_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--source-dir",
        type=Path,
        help="Root directory of the source tree.",
        default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help='Directory to place generated files.')
    parser.add_argument(
        "--conan-dir",
        type=Path,
        default=None,
        help='Directory to install Conan packages.')
    parser.add_argument(
        "--repo-conanfile",
        type=Path,
        default=Path('open/conanfile.py'),
        help='Conan recipe file requiring necessary tools (Swagger codegen and apidoctool).')

    explicit_apidoctool = parser.add_mutually_exclusive_group()
    explicit_apidoctool.add_argument(
        "--apidoctool-package-ref",
        type=str,
        help="Specifies the apidoctool Conan package reference.")
    explicit_apidoctool.add_argument(
        "--apidoctool-jar-url",
        type=str,
        help="Specifies the URL to download the apidoctool .jar from.")
    explicit_apidoctool.add_argument(
        "--apidoctool-jar",
        type=str,
        help="Specifies the path to a local apidoctool .jar file.")

    return parser.parse_args()


def main():
    args = parse_args()
    forced_apidoctool_location = (
        args.apidoctool_package_ref or args.apidoctool_jar_url or args.apidoctool_jar)

    output_dir = args.output_dir or (
        args.source_dir.parent / f'{args.source_dir.name}-openapi_schemas')
    try:
        generate_openapi_schemas(
            source_dir=args.source_dir,
            output_dir=output_dir,
            packages_dir=args.conan_dir,
            repo_conanfile=args.repo_conanfile,
            forced_apidoctool_location=forced_apidoctool_location)
    except RuntimeError as e:
        print(f'Failed to generate schemas: {e}')
        exit(1)

if __name__ == '__main__':
    main()
