#!/usr/bin/env python3

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

import json
import logging
import os
import shutil
import subprocess as sp
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator, Union

sys.path.append(str(Path(__file__).parent))
from run_apidoctool import generate_openapi_schemas
from apidoc_diff.process_json import save_sorted_json
from apidoc_diff.segment_apis import dump_endpoints

DEFAULT_CONANFILE = Path("open/conanfile.py")
# This tuple eagerly lists all present and future schemas, but the script will only compare schemas
# that exist in both the "base" and "head" versions.
API_SCHEMAS = (
    "api-v1.json",
    "api-v2.json",
    "api-v3.json",
    "api-v4.json",
    "api-v5.json",
    "api-v6.json",
    "api-v7.json",
    "api-v8.json",
    "api-deprecated.json",
    "api-legacy.json",
)


def _run(cmd: list[Union[str, Path]], check=True, log=True, silent=False):
    cmds = [str(item) for item in cmd]
    if log:
        logging.info(f"> {' '.join(cmds)}")
    sp.run(cmd, check=check, capture_output=silent)


def git(*args, silent: bool=True):
    _run(["git", *args], silent=silent)


@contextmanager
def worktree(commit_ref: str, silent: bool=True) -> Generator[Path, None, None]:
    with TemporaryDirectory(suffix="_apidiff_worktree") as temp_directory:
        try:
            git("worktree", "add", temp_directory, commit_ref, silent=silent)
            yield Path(temp_directory)
        finally:
            git("worktree", "remove", temp_directory, silent=silent)


def preprocess_json(json_path: Path):
    data = json.load(json_path.open())
    save_sorted_json(data, output_file=json_path)


def gather_apidoc(commit_ref: str, output_dir: Path, conan_dir: Path, silent: bool):
    logging.info(f"Gathering OpenAPI schemas in {str(output_dir)}")
    with worktree(commit_ref) as base_dir:
        output_dir.mkdir(parents=False, exist_ok=True)
        generate_openapi_schemas(
            source_dir=base_dir,
            repo_conanfile=DEFAULT_CONANFILE,
            output_dir=output_dir,
            packages_dir=conan_dir,
            forced_apidoctool_location=None,
            silent=silent
        )
        for schema in API_SCHEMAS:
            if (output_dir / schema).is_file():
                preprocess_json(output_dir / schema)


def segment_apis(json_path: Path):
    data = json.load(json_path.open())
    dump_endpoints(data, json_path.parent / json_path.stem)


def path_to_endpoint(relative_json_path: Path):
    return f"{relative_json_path.stem.upper()} /{relative_json_path.parent}"


def identical(first: Path, second: Path) -> bool:
    return sp.run(["cmp", str(first), str(second)], check=False, stdout=sp.PIPE).returncode == 0


def generate_diffs(base_commit_ref: str, head_commit_ref: str, silent: bool):
    # Get terminal width from environment variable or detect from terminal
    if output_width := os.environ.get("APIDOC_DIFF_OUTPUT_WIDTH"):
        output_width = int(output_width)
    else:
        # Get actual terminal width or fall back to 99 if not in a terminal
        try:
            output_width = shutil.get_terminal_size().columns
        except OSError:
            # Not a terminal or can't detect size
            output_width = 99
    with TemporaryDirectory(suffix="_apidiff") as temp_directory:
        logging.debug(f"Running in {temp_directory}")
        base_schema_dir = Path(temp_directory) / "base"
        head_schema_dir = Path(temp_directory) / "head"
        conan_dir = Path(temp_directory) / "packages"
        gather_apidoc(base_commit_ref, base_schema_dir, conan_dir, silent)
        gather_apidoc(head_commit_ref, head_schema_dir, conan_dir, silent)

        for schema in API_SCHEMAS:
            base_schema = base_schema_dir / schema
            head_schema = head_schema_dir / schema

            if base_schema.is_file():
                segment_apis(base_schema)
            else:
                logging.warning(f"{base_schema.name} does not exist in the base version")

            if head_schema.is_file():
                segment_apis(head_schema)
            else:
                logging.warning(f"{head_schema.name} does not exist in the head version")

            if not (head_schema.is_file() and base_schema.is_file()):
                logging.warning(
                    f"Skipping comparison for {schema} because it doesn't exist in both versions"
                )
                continue

            schema_sub_dir = head_schema_dir / Path(schema).stem
            for file in schema_sub_dir.rglob("*"):
                rel_name = file.relative_to(schema_sub_dir)
                matching_file = base_schema_dir / Path(schema).stem / rel_name
                if matching_file.is_file() and not identical(matching_file, file):
                    title = path_to_endpoint(rel_name)
                    print("=" * output_width)
                    print(title)
                    print("=" * output_width)
                    _run(["jd", matching_file, file], check=False, log=False)
                    _run([
                        "delta",
                        "--no-gitconfig",
                        "--dark",
                        "--paging", "never",
                        "--width", str(output_width),
                        "--wrap-max-lines", "unlimited",
                        "--file-decoration-style", "none",
                        matching_file, file],
                        check=False, log=False)
                    print()


# Custom log handler that stores logs in memory.
class MemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_records: list[logging.LogRecord] = []

    def emit(self, record):
        self.log_records.append(record)

    def flush(self):
        pass

    def print_logs(self):
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                     datefmt='%Y-%m-%d %H:%M:%S')
        for record in self.log_records:
            print(formatter.format(record), file=sys.stderr)


if __name__ == "__main__":
    try:
        # Setting up memory log handler - we collect logs instead of immediately printing them, so
        # that the delta output is printed first, which is more useful on the CI.
        memory_handler = MemoryLogHandler()
        from argparse import ArgumentParser

        parser = ArgumentParser()
        parser.add_argument("base_commit_ref", help="The diff base commit hash.")
        parser.add_argument(
            "-c", "--conanfile", help="The conanfile to use.", default=DEFAULT_CONANFILE, type=Path)
        parser.add_argument("--head", help="The diff head commit hash.", default="HEAD")
        parser.add_argument("--verbose", help="Verbose output.", default=False, action="store_true")
        parser.add_argument("--log-level", help="Set the logging level", 
                            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            default="INFO")
        args = parser.parse_args()
        
        log_level = getattr(logging, args.log_level)
        logging.basicConfig(handlers=[memory_handler], level=log_level)

        print("apidoc_diff is running. Logs will be printed at the end.")
        generate_diffs(args.base_commit_ref, args.head, not args.verbose)
    finally:
        print("\nLog output:", file=sys.stderr)
        memory_handler.print_logs()
