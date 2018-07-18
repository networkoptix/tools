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
    
JIRA_PREFIX = 'TEST-RUN'
JIRA_REASON = crash_info.Reason('Server', 'SEGFAULT', ['f1', 'f2'])


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
        jira.create_issue('server--3.1.0.311-abc-default--a.gdb-bt')
        jira.update_issue(['server--3.1.0.311-abc-default--a.gdb-bt'])
        assert jira.issue.key.startswith('VMS-')
        assert 'Open' == jira.issue.fields.status.name
        assert 'TEST-RUN Server has crashed on Linux: SEGFAULT' == jira.issue.fields.summary
        assert 'Call Stack:\n{code}\nf1\nf2\n{code}' == jira.issue.fields.description
        assert 'Server' == jira.issue.fields.customfield_10200.value
        assert 'VMS-2022' == jira.issue.fields.customfield_10009
        assert {'Server'} == jira.field_set('components')
        assert {'3.1'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a'} == jira.attachments()
        
        logger.debug('Suppose case is closed by developer')
        jira.api._transition(jira.issue.key, 'Reject')
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.debug('No reopen for the same version')
        jira.update_issue(['server--3.1.0.312-abc-default--b.gdb-bt'])
        assert 'Closed' == jira.issue.fields.status.name
        assert {'a'} == jira.attachments()

        logger.debug('Reopen is for new version')
        jira.update_issue(['server--3.2.0.321-tricom-default--c.gdb-bt'])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.1', '3.2'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a', 'c'} == jira.attachments()

        logger.debug('Suppose case is closed by developer with fix version')
        jira.api._transition(jira.issue.key, 'Reject')
        jira.issue.update(fields=dict(customfield_11120=323))
        assert 'Closed' == jira.api._jira.issue(jira.issue.key).fields.status.name

        logger.debug('No reopen should happen for report on changeset before fix')
        jira.update_issue(['server--3.2.0.322-tricom-default--d.gdb-bt'])
        assert 'Closed' == jira.issue.fields.status.name
        assert {'a', 'c'} == jira.attachments()

        logger.debug('Reopen is for new changeset')
        jira.update_issue(['server--3.2.0.323-xyz-default--e.gdb-bt'])
        assert 'Open' == jira.issue.fields.status.name
        assert {'3.1', '3.2'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'a', 'c', 'e'} == jira.attachments()

        logging.debug('Attachments rotation')
        jira.update_issue([
            'server--3.2.0.324-xyz-default--f.gdb-bt',
            'server--4.0.0.412-abc-default--g.gdb-bt',
        ])
        assert {'3.1', '3.2', '4.0'} == jira.field_set('versions')
        assert {'3.1_hotfix', '3.2'} == jira.field_set('fixVersions')
        assert {'e', 'f', 'g'} == jira.attachments()
