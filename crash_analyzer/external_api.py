#!/usr/bin/env python3

import jira
import json
import logging
import os
import requests
from typing import List, Dict

import crash_info
import utils

logger = logging.getLogger(__name__)
CRASH_MONITOR_EPIC = "VMS-2022"


class Error(Exception):
    pass


class CrashServerError(Error):
    pass


class JiraError(Error):
    pass


class CrashServer:
    def __init__(self, url: str, login: str, password: str):
        self._url = url
        self._auth = (login, password)
        if not self._url.endswith('/'):
            self._url += '/'

    def list_all(self, format: str) -> List[str]:
        """Returns list of all report names in :format from crash server.
        """
        response = self._get('list', extension=format)
        dump_names = []
        for dump in json.loads(response.text):
            path = dump['path'][1:]
            if utils.is_ascii_printable(path):
                dump_names.append(path.replace('/', '--'))

        logger.info('Found {} reports by {}'.format(len(dump_names), response.url))
        return dump_names

    def get(self, name: str) -> str:
        """Returns report content by :name.
        """
        return self._get('get', path=('/' + name.replace('--', '/'))).content

    def _get(self, api: str, **params: Dict[str, str]) -> str:
        r = requests.get(self._url + api, params=params, auth=self._auth)
        if r.status_code != 200:
            raise CrashServerError('Unable to get {} -- {}'.format(r.url, r.status_code))

        return r


class Jira:
    def __init__(self, url: str, login: str, password: str, file_limit: int, prefix: str = ''):
        self._jira = jira.JIRA(server=url, basic_auth=(login, password))
        self._file_limit = file_limit
        self._prefix = prefix + ' ' if prefix else ''

    def create_issue(self, report: crash_info.Report, reason: crash_info.Reason) -> str:
        """Creates JIRA issue by crash :report.
        Return issue key of created issue.
        """

        def team(component: str) -> str:
            try:
                return {'Server': 'Server', 'Client': 'GUI'}[component]
            except KeyError:
                raise ('Unsupported JIRA component:' + component)

        def operation_system(format: str) -> str:
            try:
                return {'gdb-bt': 'Linux', 'dmp': 'Windows'}[format]
            except KeyError:
                raise ('Unsupported JIRA format:' + format)

        issue = self._jira.create_issue(
            project='VMS',
            issuetype={'name': 'Bug'},
            summary=self._prefix + '{r.component} has crashed on {os}: {r.code}'.format(
                r=reason, os=operation_system(report.format)),
            versions=[{'name': report.version}],
            fixVersions=[{'name': report.version + '_hotfix'}],
            components=[{'name': reason.component}],
            customfield_10200={"value": team(reason.component)},
            customfield_10009=CRASH_MONITOR_EPIC,
            description='\n'.join(['Call Stack:', '{code}'] + reason.stack + ['{code}']))

        logger.info("New JIRA case {}: {}".format(issue.key, issue.fields.summary))
        return issue.key

    def update_issue(self, key: str, reports: List[crash_info.Report]) -> bool:
        """Update JIRA issue with new crash :reports.
        Returns True is issue is successfully updated.
        """
        if not reports:
            raise JiraError('Unable to update JIRA case {} with no reports'.format(key))

        issue = self._jira.issue(key)
        if issue.fields.status.name == 'Closed':
            min_fix = min(v.name for v in issue.fields.fixVersions)
            max_repro = max(d.version for d in reports)
            if min_fix > max_repro:
                logger.debug('JIRA case {} is already fixed'.format(key))
                return False
            else:
                self._transition(issue, 'Reopen')
                logger.info('Reopen JIRA case {} for version {}'.format(key, max_repro))

        issue_versions = set(v.name for v in issue.fields.versions)
        new_versions = issue_versions | set(d.version for d in reports)
        if issue_versions != new_versions:
            issue.update(fields={'versions': list({'name': v} for v in new_versions)})
            logger.debug('JIRA case {} is updated for versions: {}'.format(
                key, ', '.join(new_versions)))

        return True

    def attach_files(self, key: str, files: List[str]):
        """Attaches new :files to JIRA issue.
        """
        for path in files[-self._file_limit:]:
            name = os.path.basename(path)
            with open(path, 'rb') as f:
                self._jira.add_attachment(key, attachment=f, filename=name)

            logger.debug('JIRA case {} new attachement {}'.format(key, name))

        files = self._jira.issue(key).fields.attachment
        files.sort(key=lambda a: a.created)
        while len(files) > self._file_limit:
            self._jira.delete_attachment(files[0].id)
            logger.debug('JIRA case {} replaced attachment {}'.format(key, files[0].filename))
            del files[0]

    def _transition(self, issue: jira.Issue, *transition_names: List[str]):
        for name in transition_names:
            for transition in self._jira.transitions(issue):
                if transition['name'].startswith(name):
                    self._jira.transition_issue(issue, transition['id'])
                    continue
