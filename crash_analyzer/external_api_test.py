#!/usr/bin/env python3

import logging
from typing import List, Tuple

import pytest

import crash_info
import external_api
import utils

CONFIG = utils.resource_parse('monitor_example_config.yaml')


@pytest.fixture
def crash_server():
    return external_api.CrashServer(**CONFIG['crashServer'])


@pytest.mark.parametrize(
    "format", ['gdb-bt', 'dmp', '*']
)
def test_crash_server(crash_server: external_api.CrashServer, format: str):
    dumps = crash_server.list_all(format)
    assert len(dumps) > 100
    for i in range(3):
        assert crash_server.get(dumps[i])


class JiraFixture:
    def __init__(self):
        self.api = external_api.Jira(**CONFIG['jira'])
        self.issue = None

    def create_issue(self, report_name: str):
        report, reason = self._make_report(report_name)
        self.issue = self.api._jira.issue(self.api.create(report, reason))

    def update_issue(self, report_names: List[str]):
        self.api.update(self.issue.key, [self._make_report(n)[0] for n in report_names])
        self.issue = self.api._jira.issue(self.issue.key)

    def delete_issue(self):
        if self.issue:
            self.issue.delete()

    def attachments(self):
        return set(v.filename.split('--')[-1].split('.')[0]
                   for v in self.issue.fields.attachment)

    @staticmethod
    def _make_report(name: str) -> Tuple[crash_info.Report, crash_info.Reason]:
        report = crash_info.Report(name)
        report.find_files(utils.resource_path('jira'))
        reason = crash_info.Reason(report.component, 'SEGFAULT', ['f1', 'f2'])
        return report, reason


@pytest.fixture
def jira():
    j = JiraFixture()
    yield j
    j.delete_issue()


def test_jira(jira: JiraFixture):
    jira.create_issue('server--3.1.0.1234-abcd-default--1234.gdb-bt')
    jira.update_issue(['server--3.1.0.1234-abcd-default--1234.gdb-bt'])
    assert jira.issue.key.startswith('VMS-')
    assert 'Open', jira.issue.fields.status.name
    assert 'TEST-RUN Server has crashed on Linux: SEGFAULT' == jira.issue.fields.summary
    assert 'Call Stack:\n{code}\nf1\nf2\n{code}' == jira.issue.fields.description
    assert 'Server' == jira.issue.fields.customfield_10200.value
    assert set(['Server']) == set(c.name for c in jira.issue.fields.components)
    assert set(['3.1']) == set(v.name for v in jira.issue.fields.versions)
    assert set(['3.1_hotfix']) == set(v.name for v in jira.issue.fields.fixVersions)
    assert set(['1234']) == jira.attachments()

    logging.debug('Suppose case is closed by developer')
    jira.api._transition(jira.issue.key, 'Feedback', 'QA Passed')
    assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

    logging.debug('No reopen should happen for dump from the same version')
    jira.update_issue(['server--3.1.0.5678-xyzu-default--5678.gdb-bt'])
    assert 'Closed' == jira.issue.fields.status.name
    assert set(['1234']) == jira.attachments()

    logging.debug('Reopen is expected for dumps from new version')
    jira.update_issue([
        'server--3.2.0.2344-asdf-default--3451.gdb-bt',
        'server--3.2.0.3452-dfga-default--7634.gdb-bt',
    ])
    assert 'Open' == jira.issue.fields.status.name
    assert set(['3.1', '3.2']) == set(v.name for v in jira.issue.fields.versions)
    assert set(['1234', '3451', '7634']) == jira.attachments()

    logging.debug('First dump should be replaced by the last one')
    jira.update_issue(['server--4.0.0.1111-abcd-default--1111.gdb-bt'])
    assert set(['3.1', '3.2', '4.0']) == set(v.name for v in jira.issue.fields.versions)
    assert set(['3451', '7634', '1111']) == jira.attachments()
