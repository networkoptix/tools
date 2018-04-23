#!/usr/bin/env python3

import jira
import jira.exceptions
import json
import logging
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

    def list_all(self, **filters: Dict[str, str]) -> List[str]:
        """Returns list of all report names by :filters.
        """
        response = self._get('list', **filters)
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


def fetch_new_crashes(directory: utils.Directory, report_count: int, known_reports: set = {},
                      min_version: str = '', extension: str = '*',
                      api: type = CrashServer, thread_count: int = 5, **options):
    """Fetches :count new reports into :directory, which are not present in :known_reports and
    satisfy :min_version and :extension, returns created file names.
    """
    to_download = []
    for name in api(**options).list_all(extension=extension):
        if len(to_download) >= report_count:
            break

        if crash_info.Report(name).version < min_version or name in known_reports:
            continue

        to_download.append(name)

    logger.info('Found {} new reports on server to fetch'.format(len(to_download)))
    downloaded = []
    for name, result in zip(to_download, utils.run_concurrent(
            _fetch_crash, to_download, directory=directory, thread_count=thread_count, api=api, **options)):
        if isinstance(result, CrashServerError):
            logger.debug(result)
        elif isinstance(result, Exception):
            logger.error(result)
        else:
            downloaded.append(name)

    logger.info('Fetched {} new reports form server'.format(len(downloaded)))
    return downloaded


def _fetch_crash(name: str, directory: utils.Directory, api: type = CrashServer, **options):
    content = api(**options).get(name)
    directory.file(name).write_bytes(content)
    return len(content)


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

        def operation_system(extension: str) -> str:
            try:
                return {'gdb-bt': 'Linux', 'dmp': 'Windows'}[extension]
            except KeyError:
                raise ('Unsupported JIRA dump extension:' + extension)

        issue = self._jira.create_issue(
            project='VMS',
            issuetype={'name': 'Bug'},
            summary=self._prefix + '{r.component} has crashed on {os}: {r.code}'.format(
                r=reason, os=operation_system(report.extension)),
            versions=[{'name': report.version}],
            fixVersions=[{'name': report.version + '_hotfix'}],
            components=[{'name': reason.component}],
            customfield_10200={"value": team(reason.component)},
            customfield_10009=CRASH_MONITOR_EPIC,
            description='\n'.join(['Call Stack:', '{code}'] + reason.stack + ['{code}']))

        logger.info("New JIRA case {}: {}".format(issue.key, issue.fields.summary))
        return issue.key

    def update_issue(self, key: str, reports: List[crash_info.Report], directory: utils.Directory) -> bool:
        """Update JIRA issue with new crash :reports.
        """
        if not reports:
            raise JiraError('Unable to update JIRA case {} with no reports'.format(key))

        try:
            issue = self._jira.issue(key)
        except jira.exceptions.JIRAError:
            raise JiraError('Unable to update JIRA case {} witch does not exist'.format(key))

        if issue.fields.status.name == 'Closed':
            min_fix = min(v.name for v in issue.fields.fixVersions)
            max_report = max(d.version for d in reports)
            if min_fix > max_report:
                logger.debug('JIRA case {} is already fixed'.format(key))
                return
            else:
                self._transition(issue, 'Reopen')
                logger.info('Reopen JIRA case {} for version {}'.format(key, max_report))

        issue_versions = set(v.name for v in issue.fields.versions)
        new_versions = issue_versions | set(d.version for d in reports)
        if issue_versions != new_versions:
            issue.update(fields={'versions': list({'name': v} for v in new_versions)})
            logger.debug('JIRA case {} is updated for versions: {}'.format(
                key, ', '.join(new_versions)))

        for r in reports:
            self._attach_files(key, directory.files(r.file_mask()))

    def _attach_files(self, key: str, reports: List[utils.File]):
        """Attaches new :files to JIRA issue.
        """
        for report in reports[-self._file_limit:]:
            self._jira.add_attachment(key, attachment=report.path, filename=report.name)
            logger.debug('JIRA case {} new attachment {}'.format(key, report.name))

        reports = self._jira.issue(key).fields.attachment
        reports.sort(key=lambda a: a.created)
        while len(reports) > self._file_limit:
            self._jira.delete_attachment(reports[0].id)
            logger.debug('JIRA case {} replaced attachment {}'.format(key, reports[0].filename))
            del reports[0]

    def _transition(self, issue: jira.Issue, *transition_names: List[str]):
        for name in transition_names:
            for transition in self._jira.transitions(issue):
                if transition['name'].startswith(name):
                    self._jira.transition_issue(issue, transition['id'])
                    continue


def example_jira():
    config = utils.Resource('monitor_example_config.yaml').parse()['upload']
    config.pop('thread_count')
    return Jira(**config)._jira
