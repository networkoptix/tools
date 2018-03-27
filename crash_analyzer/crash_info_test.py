#!/usr/bin/env python3

import os
from glob import glob
from typing import Callable

import pytest

import crash_info
import utils


@pytest.mark.parametrize(
    'name, expected_report', utils.resource_parse('names.yaml').items()
)
def test_describe_path(name, expected_report):
    report = crash_info.Report(name)
    for key, value in expected_report.items():
        assert value == getattr(report, key, False), '{} in {}'.format(key, name)


@pytest.mark.parametrize(
    'name', utils.resource_parse('names_fail.yaml')
)
def test_describe_path_failures(name):
    with pytest.raises(crash_info.Error):
        print(crash_info.Report(name))


def map_files(function, directory, format):
    paths = glob(utils.resource_path(directory + '/*.' + format))
    return list(map(lambda p: (function, p), paths))


@pytest.mark.parametrize(
    'callable, path',
    map_files(crash_info.analyze_linux_gdb_bt, 'linux', 'gdb-bt') + \
    map_files(crash_info.analyze_windows_cdb_bt, 'windows', 'cdb-bt')
)
def test_analyze_bt(callable: Callable, path: str):
    name = crash_info.Report(os.path.basename(path))
    content = utils.file_content(path)
    try:
        code, stack = utils.file_content(path + '-info').split('\n\n')
    except FileNotFoundError:
        with pytest.raises(crash_info.Error):
            print(callable(name, content))
    else:
        reason = callable(name, content)
        assert code == reason.code
        assert stack.strip().splitlines() == reason.stack
        assert 64 == len(reason.crash_id())
