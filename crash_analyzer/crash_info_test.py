#!/usr/bin/env python3

import os
from typing import Callable

import pytest

import crash_info
import utils


@pytest.mark.parametrize(
    'name, expected_report', utils.Resource('names.yaml').parse().items()
)
def test_describe_path(name: str, expected_report: dict):
    report = crash_info.Report(name)
    for key, value in expected_report.items():
        assert value == getattr(report, key, False), '{} in {}'.format(key, name)


@pytest.mark.parametrize(
    'name', utils.Resource('names_fail.yaml').parse()
)
def test_describe_path_failures(name: str):
    with pytest.raises(crash_info.Error):
        print(crash_info.Report(name))


def map_files(action: Callable, directory: str, extension: str):
    resources = utils.Resource(directory, '*.' + extension).glob()
    return list(map(lambda r: (action, r), resources))


@pytest.mark.parametrize(
    'action, report',
    map_files(crash_info.analyze_linux_gdb_bt, 'linux', 'gdb-bt') + \
    map_files(crash_info.analyze_windows_cdb_bt, 'windows', 'cdb-bt')
)
def test_analyze_bt(action: Callable, report: str):
    name = crash_info.Report(os.path.basename(report.path))
    content = report.read_data()
    try:
        code, stack = utils.File(report.path + '-info').read_data().split('\n\n')
    except FileNotFoundError:
        with pytest.raises(crash_info.Error):
            print(action(name, content))
    else:
        reason = action(name, content)
        assert code == reason.code
        assert stack.strip().splitlines() == reason.stack
        assert 64 == len(reason.crash_id)


@pytest.mark.parametrize(
    'directory, extension',
    ((utils.Resource('linux'), 'gdb-bt'), (utils.Resource('windows'), 'cdb-bt'))
)
def test_analyze_files_concurrent(directory, extension):
    reports = [crash_info.Report(r.name) for r in directory.glob('*.' + extension)]
    expected = [crash_info.Report(r.name[:-5]) for r in directory.glob('*.' + extension + '-info')]
    results = crash_info.analyze_files_concurrent(reports, directory=directory.path, thread_count=2)
    assert expected == [r for r, _ in results]