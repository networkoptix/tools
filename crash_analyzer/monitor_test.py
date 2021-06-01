#!/usr/bin/env python3

import logging
import os
import multiprocessing
import functools
from typing import List, Dict
from unittest.mock import Mock

import pytest

import crash_info
import monitor
import utils

logger = logging.getLogger(__name__)


class CrashServerMock:
    def __init__(self, url: str, login: str, password: str):
        self.args = [url, login, password]

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
    def __init__(self, issues, url: str, login: str, password: str, autoclose_indicators: Dict[str, str],
                 file_limit: int, fix_versions: list, epic_link: str, prefix: str = '',
                 fallback_versions: list = []):
        self.issues = issues
        self.args = [url, login, password, file_limit, fix_versions, epic_link, prefix]

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

    def autoclose_issue_if_required(self, key: str, reason: crash_info.Reason):
        return

    def update_issue(self, key: str, reports: List[crash_info.Report], directory: utils.Directory):
        issue = self.issues[key]
        assert directory
        for report in reports:
            issue['versions'] = sorted(set(issue['versions'] + [report.version]))
            issue['attachments'] = sorted(set(issue['attachments'] + [report.name]))

        self.issues[key] = issue
        logger.info('Issue {} is updated with {} reports'.format(key, len(reports)))
        return True

    def get_issue_first_code_block(self, issue_key: str):
        return [f'Code for {issue_key}']

    def create_or_update_crash_issue(self, issue_key: str, signature: str, lines_of_code: list):
        self.issues[signature] = {
            'code': lines_of_code,
            'extension': None,
            'versions': [],
            'stack': None,
            'attachments': [],
        }

    def get_issue(self, key):
        if key in self.issues:
            component = Mock()
            component.name = 'Client'
            issue = Mock()
            issue.fields = Mock()
            issue.fields.components = [component]
            return issue
        else:
            return None


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
    "extension", ['-bt', 'gdb-bt', 'cdb-bt']
)
@pytest.mark.parametrize(
    "restart_after_each_stage", [True, False], ids=lambda c: 'restart' if c else 'simple'
)
@pytest.mark.parametrize(
    "reports_each_run", [10, 1000]
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
    possible = utils.Resource('expected_issues.yaml').parse()
    expected = {k: v for k, v in possible.items() if v['extension'].endswith(extension)}
    expected_crashes = {
        f'Code for {k}': {
            'code': [f'Code for {k}'],
            'extension': None,
            'versions': [],
            'stack': None,
            'attachments': [],
        } for k, v in possible.items() if v['extension'].endswith(extension)}
    expected.update(expected_crashes)

    assert expected == actual
