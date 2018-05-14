#!/usr/bin/env python3

import logging
import os
import  multiprocessing
import functools
from typing import List

import pytest

import crash_info
import monitor
import utils

logger = logging.getLogger(__name__)


class CrashServerMock:
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


class JiraMock:
    def __init__(self, issues, url: str, login: str, password: str,
                 file_limit: int, prefix: str = ''):
        self.issues = issues
        self.server = '{}:{} @ {} / {} {}'.format(login, password, url, file_limit, prefix)

    def create_issue(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        key = reason.crash_id[:10]  # < Shorter key for easier debug.
        self.issues[key] = {
            'code': reason.code,
            'extension': report.extension,
            'versions': [report.version],
            'stack': reason.stack,
            'attachments': [],
        }
        logger.info('Issue {} is created for {}'.format(key, reason))
        return key

    def update_issue(self, key: str, reports: List[crash_info.Report], directory: utils.Directory):
        issue = self.issues[key]
        assert directory
        for report in reports:
            issue['versions'] = sorted(set(issue['versions'] + [report.version]))
            issue['attachments'] = sorted(set(issue['attachments'] + [report.name]))

        self.issues[key] = issue
        logger.info('Issue {} is updated with {} reports'.format(key, len(reports)))
        return True


class MonitorFixture:
    def __init__(self, directory: str):
        self.manager = multiprocessing.Manager()
        self.issues = self.manager.dict()
        self.monitor = None
        self.options = utils.Resource('monitor_example_config.yaml').parse()
        self.options['options']['directory'] = directory
        self.options['fetch']['api'] = CrashServerMock
        self.options['upload']['api'] = functools.partial(JiraMock, self.issues)
        del self.options['logging']

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
    "restart_after_each_stage", [True, False]
)
@pytest.mark.parametrize(
    "reports_each_run", [1000, 10]
)
def test_monitor(monitor_fixture, extension: str, restart_after_each_stage: bool, reports_each_run: int):
    monitor_fixture.options['fetch'].update(extension=extension, report_count=reports_each_run)
    monitor_fixture.new_monitor()

    def stage_checkpoint():
        if restart_after_each_stage:
            # Emulates stop/start scenarios between stages.
            monitor_fixture.new_monitor()

    while monitor_fixture.monitor.fetch():
        stage_checkpoint()
        monitor_fixture.monitor.analyze()
        stage_checkpoint()
        monitor_fixture.monitor.upload()
        stage_checkpoint()

    actual = {k: v for k, v in monitor_fixture.issues.items()}
    expected = {k: v for k, v in utils.Resource('expected_issues.yaml').parse().items()
                if v['extension'].endswith(extension)}

    utils.File('C:/develop/var/exp.yaml').serialize(actual)
    assert expected == actual
