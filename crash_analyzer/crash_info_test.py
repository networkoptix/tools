#!/usr/bin/env python3

import os
from glob import glob
from typing import Callable

import pytest

import crash_info
import utils


@pytest.mark.parametrize(
    'name, expected_report', utils.Resource('names.yaml').parse().items()
)
def test_describe_path(name, expected_report):
    report = crash_info.Report(name)
    for key, value in expected_report.items():
        assert value == getattr(report, key, False), '{} in {}'.format(key, name)


@pytest.mark.parametrize(
    'name', utils.Resource('names_fail.yaml').parse()
)
def test_describe_path_failures(name):
    with pytest.raises(crash_info.Error):
        print(crash_info.Report(name))


def map_files(function, directory, format):
    resources = utils.Resource(directory, '*.' + format).glob()
    return list(map(lambda r: (function, r), resources))


@pytest.mark.parametrize(
    'callable, report',
    map_files(crash_info.analyze_linux_gdb_bt, 'linux', 'gdb-bt') + \
    map_files(crash_info.analyze_windows_cdb_bt, 'windows', 'cdb-bt')
)
def test_analyze_bt(callable: Callable, report: str):
    name = crash_info.Report(os.path.basename(report.path))
    content = report.read_data()
    try:
        code, stack = utils.File(report.path + '-info').read_data().split('\n\n')
    except FileNotFoundError:
        with pytest.raises(crash_info.Error):
            print(callable(name, content))
    else:
        reason = callable(name, content)
        assert code == reason.code
        assert stack.strip().splitlines() == reason.stack
        assert 64 == len(reason.crash_id())
