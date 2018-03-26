#!/usr/bin/env python3

import os

from typing import List, Tuple

import crash_info
import external_api
import utils

CONFIG = utils.resource_parse('monitor_config.yaml')

class CrashServer(utils.TestCase):
    def setUp(self):
        utils.TestCase.setUp(self)
        self.api = external_api.CrashServer(**CONFIG['crashServer'])

    def test_api_gdb_bt(self):
        self._test_api("gdb-bt")

    def test_api_dmp(self):
        self._test_api("dmp")

    def _test_api(self, format: str):
        dumps = self.api.list_all(format)
        assert len(dumps) > 100
        for i in range(5):
            content = self.api.get(dumps[i])
            assert content

class Jira(utils.TestCase):
    def setUp(self):
        utils.TestCase.setUp(self)
        self.api = external_api.Jira(**CONFIG['jira'])

    def test_create_and_update(self):
        report, reason = self._analyze('server--3.1.0.1234-abcd-default--1234.gdb-bt')
        case = self.api.create(report, reason)
        issue = self.api._jira.issue(case)
        try:
            self.api.update(case, [report])
            issue = self.api._jira.issue(case)
            # Verify newly created case.
            self.assertTrue(issue.key.startswith('VMS-'))
            self.assertEqual('Open', issue.fields.status.name)
            self.assertEqual('TEST-RUN Server has crashed on Linux: SEGFAULT', issue.fields.summary)
            self.assertEqual('Call Stack:\n{code}\nf1\nf2\n{code}', issue.fields.description)
            self.assertEqual('Server', issue.fields.customfield_10200.value)
            self.assertEqual(set([u'Server']), set(c.name for c in issue.fields.components))
            self.assertEqual(set([u'3.1']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'3.1_hotfix']), set(v.name for v in issue.fields.fixVersions))
            self.assertEqual(set([u'1234']), self._attachments(issue))

            # Suppose case is closed by developer.
            self.api._transition(issue, 'Feedback', 'QA Passed')
            issue = self.api._jira.issue(case)
            self.assertEqual(u'Closed', issue.fields.status.name)

            self.api.update(case, self._reports('server--3.1.0.5678-xyzu-default--5678.gdb-bt'))
            issue = self.api._jira.issue(case)
            # No reopen will happen for dump from the same version.
            self.assertEqual(u'Closed', issue.fields.status.name)
            self.assertEqual(set([u'1234']), self._attachments(issue))

            self.api.update(case, self._reports(
                'server--3.2.0.2344-asdf-default--3451.gdb-bt',
                'server--3.2.0.3452-dfga-default--7634.gdb-bt'))
            issue = self.api._jira.issue(case)
            # Reopen is expected for dumps from new version.
            issue = self.api._jira.issue(case)
            self.assertEqual(u'Open', issue.fields.status.name)
            self.assertEqual(set([u'3.1', u'3.2']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'1234', u'3451', u'7634']), self._attachments(issue))

            self.api.update(case, self._reports('server--4.0.0.1111-abcd-default--1111.gdb-bt'))
            issue = self.api._jira.issue(case)
            # First dump is replaced by the last one.
            self.assertEqual(set([u'3.1', u'3.2', u'4.0']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'3451', u'7634', u'1111']), self._attachments(issue))

        finally:
            issue.delete()

    @staticmethod
    def _analyze(name: str) -> Tuple[crash_info.Report, crash_info.Reason]:
        report = crash_info.Report(name)
        report.find_files(utils.resource_path('jira'))
        reason = crash_info.Reason(report.component, 'SEGFAULT', ['f1', 'f2'])
        return report, reason

    def _reports(self, *names: List[str]) -> List[crash_info.Report]:
        return list(self._analyze(n)[0] for n in names)

    @staticmethod
    def _attachments(issue):
        return set(v.filename.split('--')[-1].split('.')[0]
            for v in issue.fields.attachment)

if __name__ == '__main__':
    utils.run_unit_tests()
