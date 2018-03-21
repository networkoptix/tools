#!/usr/bin/env python

import json
import os
import yaml

import api
import crash_info
import utils

CONFIG = yaml.load(utils.resource_content('monitor_config.yaml'))

class CrashServer(utils.TestCase):
    def setUp(self):
        utils.TestCase.setUp(self)
        self.api = api.CrashServer(**CONFIG['crashServer'])

    def test_api_gdb_bt(self):
        self._test_api("gdb-bt")

    def test_api_dmp(self):
        self._test_api("dmp")

    def _test_api(self, format):
        dumps = self.api.list_all(format)
        assert len(dumps) > 100
        for i in range(5):
            content = self.api.get(dumps[i])
            assert content

class Jira(utils.TestCase):
    def setUp(self):
        utils.TestCase.setUp(self)
        self.api = api.Jira(**CONFIG['jira'])

    def test_create_case(self):
        description = self._description(
            'server--3.1.0.1234-abcd-default--1234.cdb-bt',
            code='SEGFAULT', stack=['f1', 'f2'])

        case = self.api.create(description)
        issue = self.api._jira.issue(case)
        def attachments():
            return set(v.filename.split('--')[-1].split('.')[0]
                for v in issue.fields.attachment)

        try:
            self.assertTrue(issue.key.startswith('VMS-'))
            self.assertEqual(u'Open', issue.fields.status.name)
            self.assertEqual(u'Server has crashed: SEGFAULT', issue.fields.summary)
            self.assertEqual(u'Call Stack:\n{code}\nf1\nf2\n{code}', issue.fields.description)
            self.assertEqual(set([u'3.1']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'3.1_hotfix']), set(v.name for v in issue.fields.fixVersions))
            self.assertEqual(set([u'1234']), attachments())

            self.api._transition(issue, 'Feedback', 'QA Passed')
            issue = self.api._jira.issue(case)
            self.assertEqual(u'Closed', issue.fields.status.name)

            self.api.update(case, [self._description('server--3.1.0.5678-xyzu-default--5678.cdb-bt')])

            issue = self.api._jira.issue(case)
            self.assertEqual(u'Closed', issue.fields.status.name)
            self.assertEqual(set([u'1234']), attachments())

            self.api.update(case, [
                self._description('server--3.2.0.2344-asdf-default--3451.cdb-bt'),
                self._description('server--3.2.0.3452-dfga-default--7634.cdb-bt')
            ])

            issue = self.api._jira.issue(case)
            self.assertEqual(u'Open', issue.fields.status.name)
            self.assertEqual(set([u'3.1', u'3.2']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'1234', u'3451', u'7634']), attachments())

            self.api.update(case, [self._description('server--4.0.0.1111-abcd-default--1111.cdb-bt')])

            issue = self.api._jira.issue(case)
            self.assertEqual(set([u'3.1', u'3.2', u'4.0']), set(v.name for v in issue.fields.versions))
            self.assertEqual(set([u'3451', u'7634', u'1111']), attachments())

        finally:
            issue.delete()

    @staticmethod
    def _description(name, **kwargs):
        d = crash_info.Description(name)
        d.files = [utils.resource_path('jira/' + name)]
        for k, v in kwargs.iteritems(): setattr(d, k, v)
        return d



if __name__ == '__main__':
    utils.run_ut()
