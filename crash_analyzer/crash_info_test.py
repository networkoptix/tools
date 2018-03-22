#!/usr/bin/env python3

import json
import logging
import os

from glob import glob

import crash_info
import utils

logger = logging.getLogger(__name__)

class CrashInfo(utils.TestCase):
    def test_describe_path(self):
        name_records = json.loads(utils.resource_content("names.json"))
        for name, expected_report in name_records.items():
            logger.debug(name)
            report = crash_info.Report(name)
            for key, value in expected_report.items():
                self.assertEqual(value, getattr(report, key, False))

    def test_describe_path_failures(self):
        for name in utils.resource_content("names_fail.list").split('\n'):
            logger.debug(name)
            self.assertRaises(crash_info.Error, lambda: crash_info.Report(name))

    def test_analyze_linux_gdb_bt(self):
        self._test_analyze_bt('linux', "gdb-bt")

    def test_analyze_windows_cdb_bt(self):
        self._test_analyze_bt('windows', "cdb-bt")

    def _test_analyze_bt(self, directory: str, format: str):
        dumps = glob(utils.resource_path(directory + '/*.' + format))
        assert dumps
        for dump in dumps:
            logger.debug(dump)
            try:
                code, stack = utils.file_content(dump + '-info').split('\n\n')
            except IOError:
                self.assertRaises(crash_info.Error, lambda: crash_info.analyze(dump))
            else:
                report, reason = crash_info.analyze(dump)
                self.assertEqual(code, reason.code)
                self.assertEqual(stack.strip().split('\n'), reason.stack)

if __name__ == '__main__':
    utils.run_unit_tests()
