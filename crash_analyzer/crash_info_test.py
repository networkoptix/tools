#!/usr/bin/env python3

from glob import glob

import pytest

import crash_info
import utils


def test_describe_path():
    name_records = utils.resource_parse('names.yaml')
    for name, expected_report in name_records.items():
        report = crash_info.Report(name)
        for key, value in expected_report.items():
            assert value == getattr(report, key, False), '{} in {}'.format(key, name)


def test_describe_path_failures():
    for name in utils.resource_parse('names_fail.yaml'):
        with pytest.raises(crash_info.Error):
            print(crash_info.Report(name))


@pytest.mark.parametrize(
    'directory, format', [('linux', 'gdb-bt'), ('windows', 'cdb-bt')]
)
def test_analyze_bt(directory: str, format: str):
    dumps = glob(utils.resource_path(directory + '/*.' + format))
    assert dumps
    for dump in dumps:
        try:
            code, stack = utils.file_content(dump + '-info').split('\n\n')
        except FileNotFoundError:
            with pytest.raises(crash_info.Error):
                print(crash_info.analyze(dump))
        else:
            report, reason = crash_info.analyze(dump)
            assert code == reason.code, dump
            assert stack.strip().splitlines() == reason.stack, dump
            assert 64 == len(reason.crash_id()), dump
