#!/usr/bin/env python3

import logging
import subprocess as sp
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator, Union

sys.path.append(str(Path(__file__).parent))
import run_apidoctool as rat

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


def _run(cmd: list[Union[str, Path]]):
    cmds = [str(item) for item in cmd]
    logging.info(f"> {' '.join(cmds)}")
    sp.run(cmd, check=True)


def run_apidoctool(source_dir: Path, output_dir: Path, conan_dir: Path, repo_conanfile: Path):
    rat.generate_openapi_schemas(source_dir, repo_conanfile, output_dir, packages_dir=conan_dir)


def git(*args):
    _run(["git", *args])


@contextmanager
def worktree(commit_ref: str) -> Generator[Path, None, None]:
    with TemporaryDirectory(suffix="_apidiff_worktree") as temp_directory:
        try:
            git("worktree", "add", temp_directory, commit_ref)
            yield Path(temp_directory)
        finally:
            git("worktree", "remove", temp_directory)


def gather_apidoc(commit_ref: str, output_dir: Path, conan_dir: Path):
    with worktree(commit_ref) as base_dir:
        output_dir.mkdir(parents=False, exist_ok=True)
        run_apidoctool(
            source_dir=base_dir,
            output_dir=output_dir,
            conan_dir=conan_dir,
            repo_conanfile=DEFAULT_CONANFILE,
        )


def get_oasdiff_path(source_dir: Path) -> Path:
    package_ref = rat.extract_package_references(["oasdiff"], source_dir, DEFAULT_CONANFILE)[0]
    tools = rat.get_tool_paths([package_ref])
    return tools.oasdiff_path


def run_oasdiff(base_commit_ref: str):
    with TemporaryDirectory(suffix="_apidiff") as temp_directory:
        base_schema_dir = Path(temp_directory) / "base"
        head_schema_dir = Path(temp_directory) / "head"
        conan_dir = Path(temp_directory) / "packages"
        gather_apidoc(base_commit_ref, base_schema_dir, conan_dir)
        gather_apidoc("HEAD", head_schema_dir, conan_dir)
        oasdiff = str(get_oasdiff_path(Path(".")))

        for schema in API_SCHEMAS:
            base_schema = base_schema_dir / schema
            head_schema = head_schema_dir / schema
            if not base_schema.is_file():
                logging.warning(f"{base_schema.name} does not exist in the base version")
            if not head_schema.is_file():
                logging.warning(f"{head_schema.name} does not exist in the head version")
            if base_schema.is_file() and head_schema.is_file():
                _run([
                    oasdiff,
                    "changelog",
                    str(base_schema_dir / schema),
                    str(head_schema_dir / schema),
                ])


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("base_commit_ref", help="The diff base commit hash.")
    parser.add_argument(
        "-c", "--conanfile", help="The conanfile to use.", default=DEFAULT_CONANFILE, type=Path
    )
    args = parser.parse_args()

    run_oasdiff(args.base_commit_ref)
