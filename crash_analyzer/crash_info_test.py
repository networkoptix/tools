#!/usr/bin/env python3

import os
from typing import Callable

import pytest

import crash_info
import utils


@pytest.mark.parametrize(
    'name, expected_report_fields', utils.Resource('names.yaml').parse().items()
)
def test_describe_path(name: str, expected_report_fields: dict):
    report = crash_info.Report(name)
    for key, value in expected_report_fields.items():
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
    map_files(crash_info.analyze_linux_gdb_bt, 'linux', 'gdb-bt') +
    map_files(crash_info.analyze_windows_cdb_bt, 'windows', 'cdb-bt')
)
def test_analyze_bt(action: Callable, report: str):
    name = crash_info.Report(os.path.basename(report.path))
    content = report.read_string()
    try:
        code, stack = utils.File(report.path + '-info').read_string().split('\n\n')
    except FileNotFoundError:
        with pytest.raises(crash_info.Error):
            print(action(name, content))
    else:
        reason = action(name, content)
        assert code == reason.code
        assert stack.strip().splitlines() == reason.stack
        assert 64 == len(reason.crash_id)


def test_problem_builds():
    problem_builds = crash_info.ProblemBuilds([
        '3.1.0.555 windows',
        '3.1 arm',
        '3.2 ipera',
    ])

    cases = [
        ('mediaserver--3.1.0.555-77ebc0608e38-dw--2018_windows-x64-winxp-Windows-10_624.dmp', True),
        ('mediaserver--3.1.0.555-77ebc0608e38-dw--2016_windows-x64-winnt-Windows-XP_543.dmp', True),
        ('mediaserver--3.1.0.555-77ebc0608e38-dw--2016_linux-x64-ubuntu-Ubuntu-16.04.2_835.dmp', False),
        ('mediaserver--3.1.0.987-970fdce49492-dw--2016_linux-arm-bpi-Debian-16.04.2_835.dmp', True),
        ('mediaserver--3.1.0.987-970fdce49492-dw--2016_linux-x64-ubuntu-Ubuntu-16.04.2_835.dmp', False),
        ('mediaserver--3.2.0.777-99c5cc48ae01-dw--2017_windows-x64-winxp-Windows-7_765.cdb-bt', False),
        ('mediaserver--3.2.0.987-61fbffc8dfa1-ipera--2017_windows-x64-winxp-Windows-7_765.cdb-bt', True),
        ('mediaserver--3.1.0.236-82b4cfb70abc-ipera--2016_linux-arm-bpi-Debian-16.04.2_835.dmp', True),
    ]

    for name, result in cases:
        assert result == problem_builds.is_known(crash_info.Report(name)), name


@pytest.mark.parametrize(
    'directory, extension',
    ((utils.Resource('linux'), 'gdb-bt'), (utils.Resource('windows'), 'cdb-bt'))
)
def test_analyze_reports_concurrent(directory: utils.Directory, extension: str):
    reports = [crash_info.Report(r.name) for r in directory.glob('*.' + extension)]
    expected = [crash_info.Report(r.name[:-5]) for r in directory.glob('*.' + extension + '-info')]
    results = crash_info.analyze_reports_concurrent(
        reports, directory=utils.Directory(directory.path), thread_count=8)
    assert expected == [r for r, _ in results]
