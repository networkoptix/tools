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



def _run_apidoctool(
        properties_file: Path,
        openapi_template_file: Path,
        source_dir: Path,
        output: Path,
        silent: bool) -> sp.CompletedProcess:
    apidoctool_path = Path(os.environ.get('APIDOCTOOL_JAR', '/app/apidoctool.jar'))
    if not apidoctool_path.exists():
        raise RuntimeError(f"Apidoctool does not exist: {apidoctool_path}")
    return _run([
        'java',
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
        template_file: Path,
        api_tmp_dir: Path,
        silent: bool) -> sp.CompletedProcess:
    swagger_path = Path(os.environ.get('SWAGGER_CODEGEN_JAR', '/app/cli.jar'))
    if not swagger_path.exists():
        raise RuntimeError(f"SWAGGER cli.jar does not exist: {swagger_path}")
    return _run(
        [
            'java',
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


def generate_openapi_schemas(
        source_dir: Path,
        output_dir: Path,
        silent: bool = False):
    temp_dir_object = tempfile.TemporaryDirectory()
    temp_dir = Path(temp_dir_object.name)

    swagger_output_dir = temp_dir / 'swagger_output'
    shutil.rmtree(swagger_output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in output_dir.glob('*'):
        f.unlink()

    for properties_file in source_dir.glob(f'**/{APIDOCTOOL_PROPERTIES_FILE_NAME}'):
        project_root = _heuristic_project_root(properties_file, source_dir)
        _generate_openapi_schema(
            properties_file=properties_file,
            swagger_output_dir=swagger_output_dir,
            apidoctool_output_dir=output_dir,
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
            template_file=template_file,
            api_tmp_dir=api_tmp_dir,
            silent=silent)

        output_file = apidoctool_output_dir / (
            f'{properties_dir.parents[0].name}-{properties_dir.name}.json')
        _run_apidoctool(
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
    return parser.parse_args()


def main():
    args = parse_args()

    output_dir = args.output_dir or (
        args.source_dir.parent / f'{args.source_dir.name}-openapi_schemas')
    try:
        generate_openapi_schemas(
            source_dir=args.source_dir,
            output_dir=output_dir,
            )
    except RuntimeError as e:
        print(f'Failed to generate schemas: {e}')
        exit(1)


if __name__ == '__main__':
    main()
