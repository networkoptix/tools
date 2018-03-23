#!/usr/bin/env python3

import logging
import os
import shutil
import yaml

from glob import glob
from typing import List

import crash_info
import monitor
import utils

class CrashServer:
    def list_all(self, format: str):
        print(format)
        return list(os.path.basename(f) for f in glob(utils.resource_path('*/*' + format)))

    def get(self, name: str):
        for f in glob(utils.resource_path('*/' + name)):
            return utils.file_content(f)

        assert False, 'Unable to find file: ' + name

class Jira:
    def __init__(self):
        self.cases = {}

    def create(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        key = reason.crash_id()[:10]
        self.cases[key] = dict(
            attachments = [],
            code = reason.code,
            format = report.format,
            versions = [report.version])

        logging.info('Case {} is created for {}'.format(key, reason))
        return key

    def update(self, key: str, reports: List[crash_info.Report]):
        case = self.cases[key]
        for report in reports:
            case['versions'] = sorted(set(case['versions'] + [report.version]))
            case['attachments'] = sorted(set(case['attachments'] + report.files))

        logging.info('Case {} is updated with {} reports'.format(key, len(reports)))


class Monitor(utils.TestCase):
    def setUp(self):
        super().setUp()
        self.options = monitor.Options(**utils.resource_parse('monitor_config.yaml')['options'])
        self.crash_server = CrashServer()
        self.jira = Jira()
        self.monitor = None

    def tearDown(self):
        del self.monitor
        shutil.rmtree(self.options.directory)

    def test_linux(self): self._test_monitor(format = 'gdb-bt')
    def test_windows(self): self._test_monitor(format = 'cdb-bt')
    def test_multisystem(self): self._test_monitor(format = '-bt')

    # TODO: Uncomment and fix these tests.
    #def test_partial(self): self._test_monitor(format = '-bt', reports_each_run = 5)
    #def test_remake(self): self._test_monitor(format = '-bt', reports_each_run = 5, remake = True)

    def _test_monitor(self, format, remake = False, **options):
        self.options.update(format = ('*-bt' if format == '-bt' else format), **options)
        self._new_monitor()
        while True:
            if not self.monitor.download_new_reports():
                break
            if remake:
                self._new_monitor()

            self.monitor.analyze_new_reports()
            self.monitor.upload_to_jira()
            if remake:
                self._new_monitor()

        expected_cases = {k: v for k, v in utils.resource_parse('cases.yaml').items()
            if v['format'].endswith(format)}

        self.assertEqual(expected_cases, self.jira.cases)

    def _new_monitor(self):
        del self.monitor
        self.monitor = monitor.Monitor(self.options, self.crash_server, self.jira)

if __name__ == '__main__':
    utils.run_unit_tests()
