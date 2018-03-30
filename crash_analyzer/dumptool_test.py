#!/usr/bin/env python3

import os
import shutil
from glob import glob

import pytest

import dumptool
import utils


@pytest.fixture()
def tmp_directory():
    os.makedirs('./tmp')
    yield './tmp'
    shutil.rmtree('./tmp')


def make_report_path(dump_path):
    return dump_path[:-4] + '.cdb-bt'


@pytest.mark.parametrize(
    'dump_path', list(glob(utils.resource_path('dmp/*.dmp')))
)
def test_analyze(tmp_directory, dump_path):
    tmp_dump_path = os.path.join(tmp_directory, os.path.basename(dump_path))
    shutil.copy(dump_path, tmp_dump_path)
    try:
        expected_report = utils.file_content(make_report_path(dump_path))
    except FileNotFoundError:
        with pytest.raises(dumptool.DistError):
            dumptool.analyse_dump(dump_path=tmp_dump_path, cache_directory=tmp_directory)
    else:
        content = dumptool.analyse_dump(dump_path=tmp_dump_path, cache_directory=tmp_directory)
        assert expected_report == content
        tmp_report_path = make_report_path(tmp_dump_path)
        assert expected_report == utils.file_content(tmp_report_path)



