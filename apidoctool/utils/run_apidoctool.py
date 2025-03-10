#!/usr/bin/env python3

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

import argparse
import os
import re
import shutil
import subprocess as sp
import tempfile
from typing import Optional
from pathlib import Path
from urllib.request import urlopen

SWAGGER_TEMPLATE_FILE_NAME = 'openapi_template.yaml'
APIDOCTOOL_PROPERTIES_FILE_NAME = 'apidoctool.properties'
OPEN_SOURCE_ROOT_DIR_NAME = 'open'

ENV = os.environ.copy()

PACKAGE_REQUIREMENT_REGEX = re.compile(
    r'\b(?:build_|tool_)requires\(\s*\"(?P<package_name>[\w-]+?)\/'
    r'(?P<package_version>\d+\.\d+(?:\.\d+)?)\"\s+'
    r'\"\#(?P<recipe_id>\w{32})\"')
CONAN_PACKAGE_REF_REGEX = re.compile(r'[\w-]+\/\d+\.\d+(?:\.\d+)?\@(?:\#\w{32})?')


def _run(
        cmd: list[str],
        check: bool = False,
        env: Optional[dict] = None,
        silent: bool = False) -> sp.CompletedProcess:
    return sp.run(cmd, check=check, env=env, capture_output=silent)


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
        output: Path,
        silent: bool) -> sp.CompletedProcess:
    return _run([
        str(java_path),
        '-Dfile.encoding=UTF-8',
        '-jar',
        str(apidoctool_path),
        '-verbose',
        'code-to-json',
        '-openapi-template-json',
        str(openapi_template_file),
        '-output-openapi-json',
        str(output),
        '-config',
        str(properties_file),
        '-vms-path',
        str(source_dir)
    ], check=True, silent=silent)


def _run_swagger_codegen(
        java_path: Path,
        swagger_path: Path,
        template_file: Path,
        api_tmp_dir: Path,
        silent: bool) -> sp.CompletedProcess:

    return _run(
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
        ], check=True, silent=silent)


def _install_tools(
        source_dir: Path,
        repo_conanfile: Path,
        temp_dir: Path,
        forced_apidoctool_location: Optional[str],
        silent: bool = False) -> ToolPaths:
    artifactory_url = os.getenv('NX_ARTIFACTORY_URL', 'https://artifactory.nxvms.dev/artifactory/')
    conan_url = os.getenv('NX_CONAN_URL', f'{artifactory_url}/api/conan/conan')
    (conan_user, conan_password) = (
        os.getenv('NX_ARTIFACTORY_USERNAME'), os.getenv('NX_ARTIFACTORY_PASSWORD'))

    package_names = list(ToolPaths.TOOL_DESCRIPTORS.keys())
    if _is_conan_package_ref(forced_apidoctool_location):
        package_names = list(set(package_names) - {'apidoctool'})
    package_references = extract_package_references(
        package_names=package_names, source_dir=source_dir, repo_conanfile=repo_conanfile)

    _run(['conan', 'remote', 'add', '-f', 'nx', conan_url], env=ENV, silent=silent)
    if download_cache := os.getenv('NX_CONAN_DOWNLOAD_CACHE'):
        _run(
            ['conan', 'config', 'set', f'storage.download_cache={download_cache}'],
            env=ENV,
            silent=silent
        )
    if conan_user and conan_password:
        _run(
            ['conan', 'user', '-r', 'nx', conan_user, '-p', conan_password],
            env=ENV,
            silent=silent
        )

    if _is_conan_package_ref(forced_apidoctool_location):
        package_references.append(str(forced_apidoctool_location))

    for package_reference in package_references:
        _run(['conan', 'install', '-r', 'nx', package_reference], env=ENV, silent=silent)

    tool_paths = get_tool_paths(package_references)
    if _is_url(forced_apidoctool_location):
        tool_paths.apidoctool_path = _download_apidoctool(
            url=str(forced_apidoctool_location), temp_dir=temp_dir)
    elif (not _is_conan_package_ref(forced_apidoctool_location)
          and forced_apidoctool_location is not None):
        # Assume forced_apidoctool_location is a path to a local file.
        tool_paths.apidoctool_path = Path(forced_apidoctool_location)

    return tool_paths


def _is_conan_package_ref(location: Optional[str]) -> bool:
    return bool(location) and bool(location and CONAN_PACKAGE_REF_REGEX.match(location))


def _is_url(location: Optional[str]) -> bool:
    return bool(location) \
        and bool(location and (location.startswith('http://') or location.startswith('https://')))


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


def extract_package_references(
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


def get_tool_paths(package_references: list[str]) -> ToolPaths:
    result = ToolPaths()

    for package_reference in package_references:
        conan_info_args = ['conan', 'info', '--paths', '--only', 'package_folder']
        package_info = sp.run(
            conan_info_args + [package_reference],
            env=ENV,
            encoding='utf-8',
            stdout=sp.PIPE,
            check=True)

        # Get paths for the package and its dependencies.
        package_name = ''
        for info_line in package_info.stdout.split('\n'):
            if not info_line:
                continue
            if 'package_folder' in info_line:
                _, _, package_path = info_line.partition(':')
                result.set_path_by_package_name(package_name, Path(package_path.strip()))
            else:
                package_name = info_line[:info_line.index('/')]

    return result


def generate_openapi_schemas(
        source_dir: Path,
        repo_conanfile: Path,
        output_dir: Path,
        packages_dir: Path,
        forced_apidoctool_location: Optional[str],
        silent: bool = False):
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
        forced_apidoctool_location=forced_apidoctool_location,
        silent=silent)

    for properties_file in source_dir.glob(f'**/{APIDOCTOOL_PROPERTIES_FILE_NAME}'):
        project_root = _heuristic_project_root(properties_file, source_dir)
        _generate_openapi_schema(
            properties_file=properties_file,
            swagger_output_dir=swagger_output_dir,
            apidoctool_output_dir=output_dir,
            tool_paths=tool_paths,
            source_dir=project_root,
            silent=silent)


def _get_type_header_paths(properties_file: Path) -> list[str]:
    type_header_paths = []
    content = properties_file.read_text()

    # Match 'typeHeaderPaths' followed by optional whitespace, '=', optional whitespace, and
    # capture everything after until a non-continued line or end of file.
    pattern = r'typeHeaderPaths\s*=\s*((?:[^\\,\n]+(?:\s*,\s*)?|\\\s*\n\s*)+)'
    match = re.search(pattern, content, re.MULTILINE)

    if match:
        paths_str = re.sub(r'\\\s*\n\s*', '', match.group(1))
        type_header_paths = [p.strip() for p in paths_str.split(',') if p.strip()]

    return type_header_paths


def _heuristic_project_root(properties_file: Path, source_dir: Path) -> Path:
    # Determines project root by checking if type header paths from properties file exist either
    # directly in source_dir or source_dir/open. Falls back to source_dir/open if no paths found,
    # or source_dir if no matches found.
    type_header_paths = _get_type_header_paths(properties_file)
    if not type_header_paths:
        print(f"No typeHeaderPaths found in {properties_file!r}, using "
            f"{source_dir / OPEN_SOURCE_ROOT_DIR_NAME} as project root")
        return source_dir / OPEN_SOURCE_ROOT_DIR_NAME
    for path in type_header_paths:
        if (source_dir / path).exists():
            return source_dir
    for path in type_header_paths:
        if (source_dir / OPEN_SOURCE_ROOT_DIR_NAME / path).exists():
            return source_dir / OPEN_SOURCE_ROOT_DIR_NAME
    # If no matches found, default to source_dir
    return source_dir


def _generate_openapi_schema(
        properties_file: Path,
        swagger_output_dir: Path,
        apidoctool_output_dir: Path,
        tool_paths: ToolPaths,
        source_dir: Path,
        silent: bool):
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

    try:
        _run_swagger_codegen(
            java_path=tool_paths.java_path,
            swagger_path=tool_paths.swagger_path,
            template_file=template_file,
            api_tmp_dir=api_tmp_dir,
            silent=silent)

        output_file = apidoctool_output_dir / (
            f'{properties_dir.parents[0].name}-{properties_dir.name}.json')
        _run_apidoctool(
            java_path=tool_paths.java_path,
            apidoctool_path=tool_paths.apidoctool_path,
            openapi_template_file=api_tmp_dir / 'openapi.json',
            properties_file=properties_file,
            source_dir=source_dir,
            output=output_file,
            silent=silent)
    except sp.CalledProcessError as e:
        raise RuntimeError(f"Failed to generate OpenAPI schema for {properties_file!r}: {e}\n")


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
        "-s", "--silent",
        action="store_true",
        default=False,
        help='When set, output from conan and apidoctool are silenced.')
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
