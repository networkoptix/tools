#!/usr/bin/env python

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Optional


SWAGGER_TEMPLATE_FILE_NAME = 'openapi_template.yaml'
APIDOCTOOL_PROPERTIES_FILE_NAME = 'apidoctool.properties'

ENV = os.environ.copy()

PACKAGE_NAME_REGEX = re.compile(r'\b(?:build_)requires\(\s*\"([\w-]+?)\/(\d+\.\d+(?:\.\d+)?)\"')


class ToolPaths:
    TOOL_DESCRIPTORS = {
        'swagger-codegen': {'attr_name': 'swagger', 'suffix': 'cli.jar'},
        'apidoctool': {'attr_name': 'apidoctool', 'suffix': 'apidoctool.jar'},
        'openjdk-jre': {'attr_name': 'java', 'suffix': 'bin/java'},
    }

    TOOL_PATH_SUFFIXES = {
        'swagger-codegen': 'cli.jar',
        'apidoctool': 'apidoctool.jar',
        'openjdk-jre': 'bin/java',
    }

    def __init__(self):
        self.java_path: Path
        self.apidoctool_path: Path
        self.swagger_path: Path

    def set_path_by_package_name(self, name: str, path: Path):
        if name not in self.TOOL_DESCRIPTORS:
            return
        descriptor = self.TOOL_DESCRIPTORS[name]
        setattr(self, f'{descriptor["attr_name"]}_path', path / descriptor['suffix'])


def run_apidoctool(
        java_path: Path,
        apidoctool_path: Path,
        properties_file: Path,
        openapi_template_file: Path,
        sources_dir: Path,
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
        str(sources_dir)
    ])


def run_swagger_codegen(
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


def install_tools(sources_dir: Path, repo_conanfile: Path) -> ToolPaths:
    artifactory_url = os.getenv('NX_ARTIFACTORY_URL', 'http://artifactory.nxvms.dev/artifactory/')
    conan_url = f'{artifactory_url}/api/conan/conan'
    (conan_user, conan_password) = (
        os.getenv('NX_ARTIFACTORY_USERNAME'), os.getenv('NX_ARTIFACTORY_PASSWORD'))

    package_full_names = extract_package_full_names(
        package_names=list(ToolPaths.TOOL_DESCRIPTORS.keys()),
        sources_dir=sources_dir,
        repo_conanfile=repo_conanfile)

    subprocess.run(['conan', 'remote', 'add', '-f', 'nx', conan_url], env=ENV)
    if conan_user and conan_password:
        subprocess.run(['conan', 'user', '-r', 'nx', conan_user, '-p', conan_password], env=ENV)

    for full_name in package_full_names:
        subprocess.run(['conan', 'install', '-r', 'nx', f'{full_name}@'], env=ENV)

    return get_tool_paths(package_full_names)


def extract_package_full_names(
        package_names: list, sources_dir: Path, repo_conanfile: Path) -> list[str]:
    full_package_names = []
    with open(sources_dir / repo_conanfile, 'r') as f:
        for line in f:
            if (result := PACKAGE_NAME_REGEX.search(line)):
                package_name = result.group(1)
                if package_name in package_names:
                    package_version = result.group(2)
                    full_package_names.append(f'{package_name}/{package_version}')

    return full_package_names


def get_tool_paths(package_full_names: list[str]) -> ToolPaths:
    result = ToolPaths()

    for package_name in package_full_names:
        conan_info_args = ['conan', 'info', '--paths', '--only', 'package_folder']
        package_info = subprocess.run(
            conan_info_args + [f'{package_name}@'], env=ENV, encoding='utf-8', capture_output=True)

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
        source_dir: Path, repo_conanfile: Path, output_dir: Path, packages_dir: Optional[Path]):
    tmp_dir = tempfile.TemporaryDirectory()

    swagger_output_dir = Path(tmp_dir.name) / 'swagger_output'
    shutil.rmtree(swagger_output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in output_dir.glob('*'):
        f.unlink()

    if 'CONAN_USER_HOME' not in ENV:
        ENV['CONAN_USER_HOME'] = str(
            packages_dir if packages_dir else str(Path(tmp_dir.name) / 'packages'))
    tool_paths = install_tools(sources_dir=source_dir, repo_conanfile=repo_conanfile)

    for properties_file in source_dir.glob(f'**/{APIDOCTOOL_PROPERTIES_FILE_NAME}'):
        generate_openapi_schema(
            properties_file=properties_file,
            swagger_output_dir=swagger_output_dir,
            apidoctool_output_dir=output_dir,
            tool_paths=tool_paths,
            sources_dir=source_dir)


def generate_openapi_schema(
        properties_file: Path,
        swagger_output_dir: Path,
        apidoctool_output_dir: Path,
        tool_paths: ToolPaths,
        sources_dir: Path):
    properties_dir = properties_file.parent
    template_file = properties_dir / SWAGGER_TEMPLATE_FILE_NAME
    if not template_file.exists():
        print(
            f'File {SWAGGER_TEMPLATE_FILE_NAME!r} not found in {str(properties_dir)!r}/; skipping.')

    api_tmp_dir_name = (
        f'{properties_dir.parents[1].name}-{properties_dir.parents[0].name}-{properties_dir.name}')
    api_tmp_dir = swagger_output_dir / api_tmp_dir_name
    api_tmp_dir.mkdir(parents=True)

    run_swagger_codegen(
        java_path=tool_paths.java_path,
        swagger_path=tool_paths.swagger_path,
        template_file=template_file,
        api_tmp_dir=api_tmp_dir)

    output_file = apidoctool_output_dir / (
        f'{properties_dir.parents[0].name}-{properties_dir.name}.json')
    run_apidoctool(
        java_path=tool_paths.java_path,
        apidoctool_path=tool_paths.apidoctool_path,
        openapi_template_file=api_tmp_dir / 'openapi.json',
        properties_file=properties_file,
        sources_dir=sources_dir,
        output=output_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--source-dir",
        type=Path,
        help="Root directory of the source tree.",
        default=Path(__file__).parent.parent.parent)
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / 'openapi_schemas',
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

    args = parser.parse_args()

    generate_openapi_schemas(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        packages_dir=args.conan_dir,
        repo_conanfile=args.repo_conanfile)

if __name__ == '__main__':
    main()
