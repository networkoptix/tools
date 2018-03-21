#!/usr/bin/env python

import jira
import json
import logging
import os
import requests

logger = logging.getLogger(__name__)

import utils

class CrashServer(object):
    def __init__(self, url, login, password):
        self._url = url
        self._auth = (login, password)

    def list_all(self, format):
        '''Retruns list of all report names in :format from crash server.
        '''
        request = self._get('list', extension=format)
        dump_names = []
        for dump in json.loads(request.text):
            path = dump['path'][1:]
            if utils.is_ascii_printable(path):
                dump_names.append(path.replace('/', '--'))

        logger.info('Found {} reports by {}'.format(len(dump_names), request.url))
        return dump_names

    def get(self, name):
        '''Returns report content by :name.
        '''
        return self._get('get', path=('/' + name.replace('--', '/'))).content

    def _get(self, api, **params):
        r = requests.get(self._url + api, params=params, auth=self._auth)
        if r.status_code != 200:
            raise Exception('Unable to get {} -- {}'.format(r.url, r.status_code))

        return r

class Jira(object):
    def __init__(self, url, login, password, file_limit):
        self._jira = jira.JIRA(server=url, basic_auth=(login, password))
        self._file_limit = file_limit

    def create(self, description):
        '''Creates JIRA case by crash :description.
        '''
        issue = self._jira.create_issue(
            project = 'VMS',
            issuetype = {'name': 'Bug'},
            summary = '{component} has crashed: {code}'.format(**description.__dict__),
            customfield_10200 = {'value': description.team},
            versions = [{'name': description.version}],
            fixVersions = [{'name': description.version + '_hotfix'}],
            description = '\n'.join(['Call Stack:', '{code}'] + description.stack + ['{code}']))

        try: self._attach_files(issue.key, description.files)
        except: issue.delete(); raise
        logger.info("New JIRA case {}: {}".format(issue.key, issue.fields.summary))
        return issue.key

    def update(self, key, descriptions):
        '''Update JIRA case with new crash :descriptions.
        '''
        issue = self._jira.issue(key)
        if issue.fields.status.name == 'Closed':
            minFix = min(v.name for v in issue.fields.fixVersions)
            maxRepro = max(d.version for d in descriptions)
            if minFix > maxRepro:
                logging.debug('JIRA case {} is already fixed'.format(key))
                return
            else:
                self._transition(issue, 'Reopen')
                logging.info('Reopen JIRA case {} for version {}'.format(key, maxRepro))

        issueVersions = set(v.name for v in issue.fields.versions)
        newVersions = issueVersions | set(d.version for d in descriptions)
        if issueVersions != newVersions:
            issue.update(fields = {'versions': list({'name': v} for v in newVersions) })
            logging.debug('JIRA case {} is updated for versions: {}'.format(
                key, ', '.join(newVersions)))

        self._attach_files(key, sum((d.files for d in descriptions), []))

    def _attach_files(self, key, files):
        for path in files:
            name = os.path.basename(path)
            self._jira.add_attachment(key, attachment=path, filename=name)
            logger.debug('JIRA case {} new attachement {}'.format(key, name))

        files = self._jira.issue(key).fields.attachment
        files.sort(lambda left, right: left.created < right.created)
        while len(files) > self._file_limit:
            self._jira.delete_attachment(files[0].id)
            del files[0]

    def _transition(self, issue, *transition_names):
        for name in transition_names:
            ts = filter(lambda t: t['name'].startswith(name), self._jira.transitions(issue))
            self._jira.transition_issue(issue, ts[0]['id'])

