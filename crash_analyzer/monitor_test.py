#!/usr/bin/env python3

import logging
import os
import shutil
from glob import glob
from typing import List

import pytest

import crash_info
import monitor
import utils


class CrashServer:
    def list_all(self, format: str) -> List[str]:
        return [os.path.basename(f) for f in glob(utils.resource_path('*/*' + format))]

    def get(self, name: str) -> str:
        for f in glob(utils.resource_path('*/' + name)):
            return utils.file_content(f)

        assert False, 'Unable to find file: ' + name


class Jira:
    def __init__(self):
        self.cases = {}

    def create(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        key = reason.crash_id()[:10]
        self.cases[key] = {
            'attachments': [],
            'code': reason.code,
            'format': report.format,
            'versions': [report.version]}

        logging.info('Case {} is created for {}'.format(key, reason))
        return key

    def update(self, key: str, reports: List[crash_info.Report]):
        case = self.cases[key]
        for report in reports:
            attachments = [f.replace('\\', '/') for f in report.files]
            case['versions'] = sorted(set(case['versions'] + [report.version]))
            case['attachments'] = sorted(set(case['attachments'] + attachments))
            logging.debug('Case {} attached {}'.format(key, ', '.join(report.files)))

        logging.info('Case {} is updated with {} reports'.format(key, len(reports)))

    def save(self, filename):
        import yaml  # < Debug only.
        with open(filename, 'w') as f:
            f.write(yaml.dump(self.cases, default_flow_style=False))


@pytest.fixture
def fixture():
    class Fixture:
        def __init__(self, **options):
            self.options = monitor.Options(**options)
            self.crash_server = CrashServer()
            self.jira = Jira()
            self.monitor = None

        def new_monitor(self):
            if self.monitor:
                self.monitor.flush_cache()
                self.monitor._records = []  # < Prevents flush after directory removal.

            self.monitor = monitor.Monitor(self.options, self.crash_server, self.jira)

    f = Fixture(**utils.resource_parse('monitor_example_config.yaml')['options'])
    yield f
    f.monitor._records = []  # < Prevents flush after directory removal.
    shutil.rmtree(f.options.directory)


@pytest.mark.parametrize(
    "format", ['gdb-bt', 'cdb-bt', '-bt']
)
@pytest.mark.parametrize(
    "remake", [True, False]
)
@pytest.mark.parametrize(
    "reports_each_run", [1000, 5]
)
def test_monitor(fixture, format: str, remake: bool, reports_each_run: int):
    fixture.options.update(
        format=('*-bt' if format == '-bt' else format),
        reports_each_run=reports_each_run)

    fixture.new_monitor()
    while True:
        if not fixture.monitor.download_new_reports():
            break
        if remake:
            fixture.new_monitor()

        fixture.monitor.analyze_new_reports()
        fixture.monitor.upload_to_jira()
        if remake:
            fixture.new_monitor()

    all_cases = utils.resource_parse('cases.yaml').items()
    assert {k: v for k, v in all_cases if v['format'].endswith(format)} == fixture.jira.cases
