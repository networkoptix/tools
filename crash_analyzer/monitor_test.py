#!/usr/bin/env python3

import logging
import os
import shutil
import  multiprocessing
import functools
from typing import List

import pytest

import crash_info
import monitor
import utils

logger = logging.getLogger(__name__)


class CrashServerEmulator:
    def __init__(self, url: str, login: str, password: str):
        self.server = '{}:{} @ {}'.format(login, password, url)

    @staticmethod
    def list_all(extension: str) -> List[str]:
        return [os.path.basename(f.path)
                for f in utils.Resource('*', '*' + extension).glob()]

    @staticmethod
    def get(name: str) -> str:
        for f in utils.Resource('*', name).glob():
            return f.read_bytes()

        assert False, 'Unable to find file: ' + name


class JiraEmulator:
    def __init__(self, issues, url: str, login: str, password: str, file_limit: int):
        self.issues = issues
        self.server = '{}:{} @ {} / {}'.format(login, password, url, file_limit)

    def create_issue(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        key = reason.crash_id[:10]
        self.issues[key] = {
            'attachments': [],
            'code': reason.code,
            'extension': report.extension,
            'versions': [report.version]}

        logger.info('Case {} is created for {}'.format(key, reason))
        return key

    def update_issue(self, key: str, reports: List[crash_info.Report]):
        issue = self.issues[key]
        for report in reports:
            issue['versions'] = sorted(set(issue['versions'] + [report.version]))
            issue['attachments'] = sorted(set(issue['attachments'] + [report.name]))

        self.issues[key] = issue
        logger.info('Case {} is updated with {} reports'.format(key, len(reports)))
        return True


class MonitorFixture:
    def __init__(self, directory: str):
        self.manager = multiprocessing.Manager()
        self.issues = self.manager.dict()
        self.monitor = None
        self.options = utils.Resource('monitor_example_config.yaml').parse()
        self.options['options']['directory'] = directory
        self.options['fetch']['api'] = CrashServerEmulator
        self.options['upload']['api'] = functools.partial(JiraEmulator, self.issues)

    def new_monitor(self):
        if self.monitor:
            self.monitor._records = {}  # < Prevents flush after directory removal.

        self.monitor = monitor.Monitor(**self.options)


@pytest.fixture
def monitor_fixture():
    with utils.TemporaryDirectory() as directory:
        f = MonitorFixture(directory.path)
        yield f
        f.monitor._records = []  # < Prevents flush after directory removal.


@pytest.mark.parametrize(
    "extension", ['gdb-bt', 'cdb-bt', '-bt']
)
@pytest.mark.parametrize(
    "remake", [True, False]
)
@pytest.mark.parametrize(
    "reports_each_run", [1000, 10]
)
def test_monitor(monitor_fixture, extension: str, remake: bool, reports_each_run: int):
    monitor_fixture.options['fetch'].update(extension=extension, report_count=reports_each_run)
    monitor_fixture.new_monitor()

    def checkpoint():
        if remake:
            monitor_fixture.new_monitor()

    while True:
        if not monitor_fixture.monitor.fetch():
            break

        checkpoint()
        monitor_fixture.monitor.analyze()
        checkpoint()
        monitor_fixture.monitor.upload()
        checkpoint()

    actual = {k: v for k, v in monitor_fixture.issues.items()}
    expected = {k: v for k, v in utils.Resource('expected_issues.yaml').parse().items()
                if v['extension'].endswith(extension)}

    assert expected == actual
