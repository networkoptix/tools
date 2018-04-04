#!/usr/bin/env python3

import os
import shutil

import pytest

import dumptool
import utils


@pytest.mark.skipif('sys.platform != "win32"')
@pytest.mark.parametrize('dump',  utils.Resource('dmp', '*.dmp').glob())
def test_analyze(dump):
    _test_analyze_with_tmp_directory([dump])


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.skipif('sys.platform != "win32"')
@pytest.mark.parametrize('thread_count', (1, 2, 4, 8))
def test_analyze_concurrent(thread_count):
    dumps = utils.Resource('dmp', '*.dmp').glob()
    utils.test_concurrent(_test_analyze_with_tmp_directory, dumps, thread_count)


def _test_analyze_with_tmp_directory(dumps):
    with utils.TemporaryDirectory() as directory:
        for dump in dumps:
            _test_analyze(directory, dump)


def _test_analyze(tmp_directory, dump):
        tmp_dump_path = os.path.join(tmp_directory, os.path.basename(dump.path))
        options = dict(cache_directory=tmp_directory)
        shutil.copy(dump.path, tmp_dump_path)

        def make_report_path(dump_path):
            return dump_path[:-4] + '.cdb-bt'

        try:
            expected_report = utils.File(make_report_path(dump.path)).read_data()
        except FileNotFoundError:
            with pytest.raises(dumptool.DistError):
                dumptool.analyse_dump(dump_path=tmp_dump_path, **options)
        else:
            content = dumptool.analyse_dump(dump_path=tmp_dump_path, **options)
            assert expected_report == content
            tmp_report_path = make_report_path(tmp_dump_path)
            assert expected_report == utils.File(tmp_report_path).read_data()



