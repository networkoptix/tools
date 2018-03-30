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
    'dump', utils.Resource('dmp', '*.dmp').glob()
)
def test_analyze(tmp_directory, dump):
    tmp_dump_path = os.path.join(tmp_directory, os.path.basename(dump.path))
    shutil.copy(dump.path, tmp_dump_path)
    try:
        expected_report = utils.File(make_report_path(dump.path)).read_data()
    except FileNotFoundError:
        with pytest.raises(dumptool.DistError):
            dumptool.analyse_dump(dump_path=tmp_dump_path, cache_directory=tmp_directory)
    else:
        content = dumptool.analyse_dump(dump_path=tmp_dump_path, cache_directory=tmp_directory)
        assert expected_report == content
        tmp_report_path = make_report_path(tmp_dump_path)
        assert expected_report == utils.File(tmp_report_path).read_data()



