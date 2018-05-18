#!/usr/bin/env python3

import jira
import jira.exceptions
import json
import logging
import requests
from typing import List, Dict, Union

import crash_info
import utils

logger = logging.getLogger(__name__)


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

        logger.debug('Found {} report(s) by {}'.format(len(dump_names), response.url))
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
                      min_version: str = '', extension: str = '*', max_size: Union[int, str] = 0,
                      api: type = CrashServer, thread_count: int = 5, **options):
    """Fetches :count new reports into :directory, which are not present in :known_reports and
    satisfy :min_version and :extension, returns created file names.
    """
    try:
        full_list = api(**options).list_all(extension=extension)
    except (CrashServerError, json.decoder.JSONDecodeError) as error:
        logger.warning(utils.format_error(error))
        return []
    
    to_download_groups = {}
    for name in full_list:
        try:
            report = crash_info.Report(name)

        except crash_info.ReportNameError as error:
            logger.warning(str(error))
            continue

        if report.build == '0' or report.version < min_version or name in known_reports:
            continue

        # Download and process reports from different components on different platforms equally often.
        key = '{} ({})'.format(report.component, report.extension)
        to_download_groups.setdefault(key, []).append(name)

    for source, names in to_download_groups.items():
        logger.debug('Found {} report(s) from VMS {}'.format(len(names), source))

    to_download = utils.mixed_merge(list(to_download_groups.values()), limit=report_count)
    downloaded = []
    for name, result in zip(to_download, utils.run_concurrent(
            _fetch_crash, to_download, directory=directory, thread_count=thread_count,
            api=api, max_size=max_size, **options)):
        if isinstance(result, CrashServerError):
            logger.debug(utils.format_error(result))
        elif isinstance(result, Exception):
            logger.error(utils.format_error(result))
        else:
            downloaded.append(name)

    logger.info('Fetched {} new report(s)'.format(len(downloaded)))
    return downloaded


def _fetch_crash(name: str, directory: utils.Directory, api: type = CrashServer,
                 max_size: Union[int, str] = 0, **options):
    content = api(**options).get(name)
    size = utils.Size(len(content))
    if size > utils.Size(max_size):
        raise CrashServerError('Report of size {}B is too big: {}'.format(size, name))

    directory.file(name).write_bytes(content)
    return len(content)


class Jira:
    def __init__(self, url: str, login: str, password: str, file_limit: int, epic_link: str, prefix: str = ''):
        self._jira = jira.JIRA(server=url, basic_auth=(login, password))
        self._file_limit = file_limit
        self.epic_link = epic_link
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

        try:
            issue = self._jira.create_issue(
                project='VMS',
                issuetype={'name': 'Crash'},
                summary=self._prefix + '{r.component} has crashed on {os}: {r.code}'.format(
                    r=reason, os=operation_system(report.extension)),
                versions=[{'name': report.version}],
                fixVersions=[{'name': report.version + '_hotfix'}],
                components=[{'name': reason.component}],
                customfield_10200={"value": team(reason.component)},
                customfield_10009=self.epic_link,
                description='\n'.join(['Call Stack:', '{code}'] + reason.stack + ['{code}']))
        except jira.exceptions.JIRAError as error:
            logger.debug(utils.format_error(error))
            raise JiraError('Unable to create issue for "{}": {}'.format(report.name, error.text))

        logger.info("New JIRA issue {}: {}".format(issue.key, issue.fields.summary))
        return issue.key

    def update_issue(self, key: str, reports: List[crash_info.Report], directory: utils.Directory) -> bool:
        """Update JIRA issue with new crash :reports.
        """
        if not reports:
            raise JiraError('Unable to update issue {} with no reports'.format(key))

        try:
            issue = self._jira.issue(key)
        except jira.exceptions.JIRAError as error:
            logger.debug(utils.format_error(error))
            raise JiraError('Unable to update issue {}: {}'.format(key, error.text))

        if issue.fields.status.name == 'Closed':
            min_fix = min(v.name for v in issue.fields.fixVersions)
            max_report = max(d.version for d in reports)
            if min_fix > max_report:
                logger.debug('JIRA issue {} is already fixed'.format(key))
                return
            else:
                self._transition(issue, 'Reopen')
                logger.info('Reopen JIRA issue {} for version {}'.format(key, max_report))

        issue_versions = set(v.name for v in issue.fields.versions)
        new_versions = issue_versions | set(d.version for d in reports)
        if issue_versions != new_versions:
            issue.update(fields={'versions': list({'name': v} for v in new_versions)})
            logger.debug('JIRA issue {} is updated for versions: {}'.format(
                key, ', '.join(new_versions)))

        for r in reports:
            self._attach_files(key, directory.files(r.file_mask()))

    def all_issues(self):
        issues = []
        for issue in self._jira.search_issues('summary ~ "has crashed on"', maxResults=1000):
            summary = issue.fields.summary
            if summary.startswith(self._prefix) and 'has crashed on' in summary:
                issues.append(issue)
        return issues

    def _attach_files(self, key: str, reports: List[utils.File]):
        """Attaches new :files to JIRA issue.
        """
        for report in reports[-self._file_limit:]:
            try:
                self._jira.add_attachment(key, attachment=report.path, filename=report.name)

            except jira.exceptions.JIRAError as error:
                message = 'Unable to attach "{}" file to JIRA issue {}: {}'.format(
                    report.name, key, error.text)
                if error.status_code == 413: #< HTTP Code: Payload Too Large.
                    logging.warning(message)
                else:
                    raise JiraError(message)
            else:
                logger.debug('JIRA issue {} new attachment {}'.format(key, report.name))

        try:
            reports = self._jira.issue(key).fields.attachment
            reports.sort(key=lambda a: a.created)
            while len(reports) > self._file_limit:
                first = reports.pop(0)
                self._jira.delete_attachment(first.id)
                logger.debug('JIRA issue {} removed attachment {}'.format(key, first.filename))

        except jira.exceptions.JIRAError as error:
            logger.debug(utils.format_error(error))
            raise JiraError('Unable to cleanup attachments at issue {}: {}'.format(key, error.text))

    def _transition(self, issue: jira.Issue, *transition_names: List[str]):
        for name in transition_names:
            for transition in self._jira.transitions(issue):
                if transition['name'].startswith(name):
                    self._jira.transition_issue(issue, transition['id'])
                    continue
