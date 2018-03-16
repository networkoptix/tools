#!/usr/bin/env python

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
        for name, expected_description in name_records.iteritems():
            logger.debug(name)
            description = crash_info.Description(name)
            for key, value in expected_description.iteritems():
                self.assertEqual(value, getattr(description, key, False))

    def test_describe_path_failures(self):
        for name in utils.resource_content("names_fail.list").split('\n'):
            logger.debug(name)
            self.assertRaises(crash_info.Error, lambda: crash_info.Description(name))

    def test_describe_linux_gdb_bt(self):
        self._test_describe_bt('describe_linux_gdb_bt', 'linux', "gdb-bt")

    def test_describe_windows_cdb_bt(self):
        self._test_describe_bt('describe_windows_cdb_bt', 'windows', "cdb-bt")

    def _test_describe_bt(self, function, directory, format):
        dumps = glob(utils.resource_path(directory + '/*.' + format))
        assert dumps
        for dump in dumps:
            logger.debug(dump)
            description = crash_info.Description(os.path.basename(dump))
            describe_bt = getattr(description, function)
            try:
                code, stack = utils.file_content(dump + '-info').split('\n\n')
            except IOError:
                self.assertRaises(crash_info.Error, lambda: describe_bt(utils.file_content(dump)))
            else:
                describe_bt(utils.file_content(dump))
                self.assertEqual(code, description.code)
                self.assertEqual(stack.strip().split('\n'), description.stack)

    def _file(self, filename):
        return os.path.join(
            os.path.dirname(__file__), 'crash_info_test', filename)

if __name__ == '__main__':
    utils.run_ut()
