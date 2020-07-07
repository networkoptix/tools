#!/usr/bin/env python3

import logging
from typing import List, Tuple

import pytest

import crash_info
import external_api
import utils

logger = logging.getLogger(__name__)

CONFIG = utils.Resource('monitor_example_config.yaml').parse()
SERVER_CONFIG = {k: v for k, v in CONFIG['fetch'].items() if k in (
    'url', 'login', 'password')}

JIRA_CONFIG = {k: v for k, v in CONFIG['upload'].items() if k in (
    'url', 'login', 'password', 'fix_versions', 'epic_link')}
AUTOCLOSE_INDICATORS = CONFIG['issue_autoclose_indicators']

JIRA_PREFIX = 'TEST-RUN'
JIRA_REASON = crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'], ['f1', 'f2'])


@pytest.mark.parametrize("extension", ['gdb-bt', 'dmp', '*'])
def test_crash_server(extension: str):
    _test_crash_server(extension)


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.parametrize('thread_count', (1, 5, 10, 20, 30))
def test_crash_server_concurrent(thread_count: int):
    utils.test_concurrent(_test_crash_server, ['dmp'], thread_count)


@pytest.mark.parametrize("extension", ['gdb-bt', 'dmp', '*'])
def test_fetch_new_crashes(extension: str):
    with utils.TemporaryDirectory() as directory:
        options = dict(CONFIG['fetch'])
        options.update(report_count=2, extension=extension)
        new = external_api.fetch_new_crashes(directory, **options)
        assert 2 == len(new)


def _test_crash_server(extension: str):
    server = external_api.CrashServer(**SERVER_CONFIG)
    dumps = server.list_all(extension=extension)
    assert len(dumps) > 10
    for i in range(2):
        assert server.get(dumps[i])


class JiraFixture:
    def __init__(self, autoclose_indicators=None):
        self.api = external_api.Jira(**JIRA_CONFIG, autoclose_indicators=autoclose_indicators,
                                     file_limit=4, prefix=JIRA_PREFIX)
        self.issue = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.issue:
            self.issue.delete()

    def create_issue(self, name: str):
        self.issue = self.api._jira.issue(self.api.create_issue(
            crash_info.Report(name),
            crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'], ['f1', 'f2'])))

    def autoclose_issue(self, reason: crash_info.Reason):
        self.api.autoclose_issue_if_required(self.issue.key, reason)
        self.issue = self.api._jira.issue(self.issue.key)

    def update_issue(self, names: List[str]):
        self.api.update_issue(self.issue.key, [crash_info.Report(n) for n in names],
                              directory=utils.Resource('jira').directory())
        self.issue = self.api._jira.issue(self.issue.key)

    def attachments(self):
        names = [a.filename for a in self.issue.fields.attachment]
        logger.debug('Attachments: {}'.format(names))
        return set(n.split('--')[-1].split('.')[0] for n in names)

    def field_set(self, name):
        return {v.name for v in getattr(self.issue.fields, name)}

    @staticmethod
    def _report(name: str) -> Tuple[crash_info.Report, crash_info.Reason]:
        report = crash_info.Report(name)
        reason = crash_info.Reason(report.component, 'SEGFAULT', ['f1', 'f2'], ['f1', 'f2'])
        return report, reason


def test_jira():
    _test_jira()


@pytest.mark.skip(reason='Helps to find out optimal thread count')
@pytest.mark.parametrize('thread_count', (1, 5, 10, 20, 30, 40))
def test_jira_concurrent(thread_count):
    utils.test_concurrent(_test_jira, None, thread_count)


def _test_jira():
    with JiraFixture() as jira:
        jira.create_issue('server--3.1.0.311-abc-default--linux-x64--a.gdb-bt')
        jira.update_issue(['server--3.1.0.311-abc-default--linux-x64--a.gdb-bt'])
        assert jira.issue.key.startswith('VMS-')
        assert 'Open' == jira.issue.fields.status.name
        assert 'TEST-RUN Server has crashed on Linux: SEGFAULT' == jira.issue.fields.summary
        assert 'Call Stack:\n{code}\nf1\nf2\n{code}' == jira.issue.fields.description
        assert 'VMS-2022' == jira.issue.fields.customfield_10009
        assert {'Server'} == jira.field_set('components')
        assert {'3.1'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a'} == jira.attachments()

        logger.info('Suppose case is rejected by developer')
        jira.api._transition(jira.issue.key, 'Close', resolution={'name': 'Rejected'})
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.info('No reopen by any version')
        jira.update_issue(['server--3.2.0.321-tricom-default--linux-x86--c.gdb-bt'])
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.info('Suppose case is fixed by developer')
        jira.api._transition(jira.issue.key, 'Reopen')
        assert 'Open' == jira.api._jira.issue(jira.issue.key).fields.status.name
        jira.api._transition(jira.issue.key, 'Start Development', 'Review', 'Close')
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.info('No reopen for the same version')
        jira.update_issue(['server--3.1.0.312-abc-default--arm-bpi--b.gdb-bt'])
        assert 'Closed' == jira.issue.fields.status.name
        assert {'a'} == jira.attachments()

        logger.info('Reopen is for new version')
        jira.update_issue(['server--3.2.0.321-uvi-tricom--linux-x86--c.gdb-bt'])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.1', '3.2'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a', 'c'} == jira.attachments()

        logger.info('No new fix version if the newer ones are set')
        jira.update_issue(['server--3.0.0.301-abc-default--linux-x64--h.gdb-bt'])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.0', '3.1', '3.2'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a', 'c', 'h'} == jira.attachments()

        logger.info('Suppose case is closed by developer with fix version')
        jira.api._transition(jira.issue.key, 'Close')
        jira.issue.update(fields=dict(customfield_11120=323))
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.info('No reopen should happen for report on changeset before fix')
        jira.update_issue(['server--3.2.0.322-uvi-tricom--arm-rpi--d.gdb-bt'])
        assert 'Closed' == jira.issue.fields.status.name
        assert {'a', 'c', 'h'} == jira.attachments()

        logger.info('Reopen is for new changeset')
        jira.update_issue(['server--3.2.0.323-xyz-default--arm-rpi--e.gdb-bt'])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.0', '3.1', '3.2'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a', 'c', 'e', 'h'} == jira.attachments()

        logger.info('Suppose developer set fix version future')
        jira.api._update_field_values(jira.issue, 'fixVersions', {'Future'})
        jira.issue.update(fields={'fixVersions': [{'name': 'Future'}]})
        assert {'Future'} == jira.field_set('fixVersions')

        logging.info('Attachments rotation without fix version update')
        jira.update_issue(['server--3.2.0.324-xyz-default--arm-rpi--f.gdb-bt'])
        assert {'3.0', '3.1', '3.2'} == jira.field_set('versions')
        assert {'Future'} == jira.field_set('fixVersions')
        assert {'c', 'e', 'f', 'h'} == jira.attachments()

        logger.info('Suppose issue is marked as duplicate')
        jira.api._transition(jira.issue.key, 'Close', resolution={'name': 'Duplicate'})
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logging.info('Attachments rotation still happens')
        jira.update_issue(['server--4.0.0.412-abc-default--linux-x86--g.gdb-bt'])
        assert {'3.0', '3.1', '3.2', '4.0'} == jira.field_set('versions')
        assert {'Future'} == jira.field_set('fixVersions')
        assert {'e', 'f', 'g', 'h'} == jira.attachments()

        logging.info('Issue must be reopened if the problem reproduced in the next version')
        assert 'Open' == jira.issue.fields.status.name


def test_jira_autoclose():
    with JiraFixture(AUTOCLOSE_INDICATORS) as jira:
        jira.create_issue('server--3.1.0.311-abc-default--linux-x64--a.gdb-bt')
        jira.update_issue(['server--3.1.0.311-abc-default--linux-x64--a.gdb-bt'])
        jira.autoclose_issue(crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'], ['f1', 'Zorz::create_sys', 'f2']))
        assert jira.issue.key.startswith('VMS-')
        assert 'Closed' == jira.issue.fields.status.name
        assert 'TEST-RUN Server has crashed on Linux: SEGFAULT' == jira.issue.fields.summary
        assert 'Call Stack:\n{code}\nf1\nf2\n{code}' == jira.issue.fields.description
        assert 'VMS-2022' == jira.issue.fields.customfield_10009
        assert {'Server'} == jira.field_set('components')
        assert {'3.1'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a'} == jira.attachments()
        assert 1 == len(jira.issue.fields.comment.comments)
        assert "Rejected" == jira.issue.fields.resolution.name

        jira.api._transition(jira.issue.key, 'Reopen')
        jira.autoclose_issue(
            crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'], ['f1', 'f2', 'f3', 'f4', 'Qt5Core!qBadAlloc', 'f5']))
        assert 'Closed' == jira.issue.fields.status.name
        assert "Rejected" == jira.issue.fields.resolution.name
