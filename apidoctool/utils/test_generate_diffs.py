#!/usr/bin/env python3

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

"""
Pytest tests for apidoc_diff.generate_diffs().

Test data
---------
Each case lives under tests/cases/<name>/ and contains:

    base/
        api/apidoctool.properties   Properties pointing to handlers.cpp / types.h
        api/openapi_template.yaml   Minimal OpenAPI 3.0 template for swagger-codegen
        api/types.h                 C++ struct definitions with %apidoc comments
        api/handlers.cpp            C++ handler registrations with %apidoc comments

    head/                           Same layout, reflecting the "after" state

    expected_diff.json              Sorted list of "METHOD /path" labels, or empty.

Requirements
------------
The following tools must be on PATH / at the configured jar paths:
  - java
  - apidoctool.jar  (APIDOCTOOL_JAR env var, default /app/apidoctool.jar)
  - swagger-codegen cli.jar  (SWAGGER_CODEGEN_JAR env var, default /app/cli.jar)
"""
import importlib.util
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pytest

# Import apidoc_diff.py explicitly by path to avoid Python resolving the name
# to the apidoc_diff/ package folder that lives alongside it.
_spec = importlib.util.spec_from_file_location(
    "apidoc_diff", Path(__file__).parent / "apidoc_diff.py")
apidoc_diff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apidoc_diff)

CASES_DIR = Path(__file__).parent / "tests" / "cases"

BASE_REF = "base_ref"
HEAD_REF = "head_ref"


@pytest.fixture
def mock_worktree(monkeypatch, case_dir):
    """
    Replace worktree() with a context manager that yields a temporary copy of
    the fixture's base/ or head/ source tree, keyed on commit ref.
    """

    # noinspection PyUnusedLocal
    @contextmanager
    def _worktree(commit_ref: str, silent: bool = True) -> Generator[Path, None, None]:
        slot = "base" if commit_ref == BASE_REF else "head"
        fixture_dir = case_dir / slot
        with tempfile.TemporaryDirectory(suffix="_mock_worktree") as tmp:
            tmp_path = Path(tmp)
            shutil.copytree(fixture_dir, tmp_path, dirs_exist_ok=True)
            yield tmp_path

    monkeypatch.setattr(apidoc_diff, "worktree", _worktree)


@pytest.fixture
def mock_run(monkeypatch):
    """Silence jd/delta viewer calls; the comparison logic itself is unaffected."""
    monkeypatch.setattr(apidoc_diff, "_run", lambda *args, **kwargs: None)


# ---------------------------------------------------------------------------
# Test data discovery
# ---------------------------------------------------------------------------

def _discover_cases() -> list[Path]:
    if not CASES_DIR.is_dir():
        return []
    return sorted(
        p for p in CASES_DIR.iterdir()
        if p.is_dir()
        and (p / "base").is_dir()
        and (p / "head").is_dir()
        and (p / "expected_diff.json").is_file()
        )


def _load_expected(path: Path) -> list[str]:
    return sorted(json.loads(path.read_text(encoding="utf-8")))


def _collect_printed_endpoints(capsys) -> list[str]:
    """
    generate_diffs() prints separator lines and endpoint label lines to stdout.
    Extract only the label lines, which have the form 'METHOD /path'.
    """
    endpoints = []
    for line in capsys.readouterr().out.splitlines():
        stripped = line.strip("=").strip()
        parts = stripped.split()
        if len(parts) == 2 and parts[0].isupper() and parts[1].startswith("/"):
            endpoints.append(stripped)
    return sorted(endpoints)


@pytest.mark.parametrize("case_dir", _discover_cases(), ids=lambda p: p.name)
def test_generate_diffs(
        case_dir: Path,
        mock_worktree,
        mock_run,
        capsys: pytest.CaptureFixture,
        ) -> None:
    apidoc_diff.generate_diffs(BASE_REF, HEAD_REF, silent=True)
    actual = _collect_printed_endpoints(capsys)
    expected = _load_expected(case_dir / "expected_diff.json")
    assert actual == expected, (
        f"\nCase: {case_dir.name}"
        f"\n  expected: {expected}"
        f"\n  actual:   {actual}",
        )
