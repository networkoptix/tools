#!/usr/bin/env python3

import logging
from typing import List, Tuple

import pytest

import crash_info
import external_api
import utils

logger = logging.getLogger(__name__)

CONFIG = utils.Resource('monitor_example_config.yaml').parse()
SERVER_FIELDS = ('url', 'login', 'password')
SERVER_CONFIG = {k: v for k, v in CONFIG['fetch'].items() if k in SERVER_FIELDS}
JIRA_CONFIG = {k: v for k, v in CONFIG['upload'].items() if k in SERVER_FIELDS}
JIRA_PREFIX = 'TEST-RUN'
JIRA_REASON = crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'])


@pytest.mark.parametrize("extension", ['gdb-bt', 'dmp', '*'])
def test_crash_server(extension: str):
    _test_crash_server(extension)


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.parametrize('thread_count', (1, 5, 10, 20, 30))
def test_crash_server_concurrent(thread_count):
    utils.test_concurrent(_test_crash_server, ['dmp'], thread_count)


@pytest.mark.parametrize("extension", ['gdb-bt', 'dmp', '*'])
def test_crash_server_fetch_new(extension):
    with utils.TemporaryDirectory() as directory:
        assert len(external_api.fetch_new_crashes(
            directory, extension=extension, **CONFIG['fetch'])) == 20


def _test_crash_server(extension: str):
    server = external_api.CrashServer(**SERVER_CONFIG)
    dumps = server.list_all(extension=extension)
    assert len(dumps) > 100
    for i in range(2):
        assert server.get(dumps[i])


class JiraFixture:
    def __init__(self):
        self.api = external_api.Jira(**JIRA_CONFIG, file_limit=3, prefix=JIRA_PREFIX)
        self.issue = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.issue:
            self.issue.delete()

    def create_issue(self, name: str):
        self.issue = self.api._jira.issue(self.api.create_issue(
            crash_info.Report(name),
            crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'])))

    def update_issue(self, names: List[str]):
        if self.api.update_issue(self.issue.key, [crash_info.Report(n) for n in names]):
            self.api.attach_files(self.issue.key, [utils.Resource('jira', n).path for n in names])

        self.issue = self.api._jira.issue(self.issue.key)

    def attachments(self):
        names = [a.filename for a in self.issue.fields.attachment]
        logger.debug('Attachments: {}'.format(names))
        return set(n.split('--')[-1].split('.')[0] for n in names)

    @staticmethod
    def _report(name: str) -> Tuple[crash_info.Report, crash_info.Reason]:
        report = crash_info.Report(name)
        reason = crash_info.Reason(report.component, 'SEGFAULT', ['f1', 'f2'])
        return report, reason


def test_jira():
    _test_jira()


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.parametrize('thread_count', (1, 5, 10, 20, 30, 40))
def test_jira_concurrent(thread_count):
    utils.test_concurrent(_test_jira, None, thread_count)


def _test_jira():
    with JiraFixture() as jira:
        jira.create_issue('server--3.1.0.1234-abcd-default--1234.gdb-bt')
        jira.update_issue(['server--3.1.0.1234-abcd-default--1234.gdb-bt'])
        assert jira.issue.key.startswith('VMS-')
        assert 'Open', jira.issue.fields.status.name
        assert 'TEST-RUN Server has crashed on Linux: SEGFAULT' == jira.issue.fields.summary
        assert 'Call Stack:\n{code}\nf1\nf2\n{code}' == jira.issue.fields.description
        assert 'Server' == jira.issue.fields.customfield_10200.value
        assert {'Server'} == {c.name for c in jira.issue.fields.components}
        assert {'3.1'} == {v.name for v in jira.issue.fields.versions}
        assert {'3.1_hotfix'} == {v.name for v in jira.issue.fields.fixVersions}
        assert {'1234'} == jira.attachments()

        logger.debug('Suppose case is closed by developer')
        jira.api._transition(jira.issue.key, 'Feedback', 'QA Passed')
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.debug('No reopen should happen for dump from the same version')
        jira.update_issue(['server--3.1.0.5678-xyzu-default--5678.gdb-bt'])
        assert 'Closed' == jira.issue.fields.status.name
        assert {'1234'} == jira.attachments()

        logger.debug('Reopen is expected for dumps from new version')
        jira.update_issue([
            'server--3.2.0.2344-asdf-default--3451.gdb-bt',
            'server--3.2.0.3452-dfga-default--7634.gdb-bt',
        ])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.1', '3.2'} == {v.name for v in jira.issue.fields.versions}
        assert {'1234', '3451', '7634'} == jira.attachments()

        logging.debug('First dump should be replaced by the last one')
        jira.update_issue(['server--4.0.0.1111-abcd-default--1111.gdb-bt'])
        assert {'3.1', '3.2', '4.0'} == {v.name for v in jira.issue.fields.versions}
        assert {'3451', '7634', '1111'} == jira.attachments()
