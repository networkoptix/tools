#!/usr/bin/env python3

import os
import shutil
from typing import List

import pytest

import dump_tool
import utils


@pytest.mark.skipif('sys.platform != "win32"')
@pytest.mark.parametrize('report',  utils.Resource('dmp', '*.dmp').glob())
def  test_analyze(report):
    _test_analyze_with_tmp_directory([report])


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.skipif('sys.platform != "win32"')
@pytest.mark.parametrize('thread_count', (1, 2, 4, 8))
def test_analyze_concurrent(thread_count):
    reports = utils.Resource('dmp', '*.dmp').glob()
    utils.test_concurrent(_test_analyze_with_tmp_directory, reports, thread_count)


def _test_analyze_with_tmp_directory(reports: List[utils.File]):
    with utils.TemporaryDirectory() as directory:
        for report in reports:
            _test_analyze(directory, report)


def _test_analyze(directory: utils.Directory, report: utils.File):
    tmp_dump_path = directory.file(report.name).path
    options = dict(cache_directory=directory.path)
    shutil.copy(report.path, tmp_dump_path)

    def make_report_path(dump_path):
        return dump_path[:-4] + '.cdb-bt'

    try:
        expected_report = utils.File(make_report_path(report.path)).read_string()
    except FileNotFoundError:
        with pytest.raises(dump_tool.DistError):
            dump_tool.analyse_dump(dump_path=tmp_dump_path, **options)
    else:
        content = dump_tool.analyse_dump(dump_path=tmp_dump_path, **options)
        assert expected_report == content
        tmp_report_path = make_report_path(tmp_dump_path)
        assert expected_report == utils.File(tmp_report_path).read_string()



