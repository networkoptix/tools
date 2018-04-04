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
        logger.debug('Emulate Crash Server {}, credentials {}:{}'.format(url, login, password))

    @staticmethod
    def list_all(extension: str) -> List[str]:
        return [os.path.basename(f.path)
                for f in utils.Resource('*', '*' + extension).glob()]

    @staticmethod
    def get(name: str) -> str:
        for f in utils.Resource('*', name).glob():
            return f.read_data()

        assert False, 'Unable to find file: ' + name


class JiraEmulator:
    def __init__(self, issues, url: str, login: str, password: str, file_limit: int):
        self.issues = issues
        logger.debug('Emulate Jira API {}, credentials {}:{}, limit {}'.format(
            url, login, password, file_limit))

    def create_issue(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        key = reason.crash_id[:10]
        self.issues[key] = {
            'attachments': [],
            'code': reason.code,
            'format': report.format,
            'versions': [report.version]}

        logger.info('Case {} is created for {}'.format(key, reason))
        return key

    def update_issue(self, key: str, reports: List[crash_info.Report]):
        issue = self.issues[key]
        for report in reports:
            issue['versions'] = sorted(set(issue['versions'] + [report.version]))

        self.issues[key] = issue
        logger.info('Case {} is updated with {} reports'.format(key, len(reports)))
        return True

    def attach_files(self, key: str, files: List[str]):
        attachments = [f.replace('\\', '/') for f in files]
        issue = self.issues[key]
        issue['attachments'] = sorted(set(issue['attachments'] + attachments))
        self.issues[key] = issue
        logger.info('Case {} attached {}'.format(key, ', '.join(attachments)))


@pytest.fixture
def fixture():
    class Fixture:
        def __init__(self, directory):
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

    with utils.TemporaryDirectory() as directory:
        f = Fixture(directory)
        yield f
        f.monitor._records = []  # < Prevents flush after directory removal.


@pytest.mark.parametrize(
    "extension", ['gdb-bt', 'cdb-bt', '-bt']
)
@pytest.mark.parametrize(
    "remake", [True, False]
)
@pytest.mark.parametrize(
    "reports_each_run", [1000, 5]
)
def test_monitor(fixture, extension: str, remake: bool, reports_each_run: int):
    fixture.options['fetch'].update(extension=extension, report_count=reports_each_run)
    fixture.new_monitor()

    def checkpoint():
        if remake:
            fixture.new_monitor()

    while True:
        if not fixture.monitor.fetch():
            break

        checkpoint()
        fixture.monitor.analyze()
        checkpoint()
        fixture.monitor.upload()
        checkpoint()

    all_cases = utils.Resource('cases.yaml').parse().items()
    assert {k: v for k, v in all_cases if v['extension'].endswith(extension)} == fixture.jira.cases
