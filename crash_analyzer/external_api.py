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


# This is required to minimize log cluttering. Set to False for more detailed debug.
CLEANUP_JIRA_EXCEPTIONS = True


class Error(Exception):
    pass


class CrashServerError(Error):
    pass


class JiraError(Error):
    def __init__(self, message: str, jira_error: jira.exceptions.JIRAError = None):
        if jira_error and CLEANUP_JIRA_EXCEPTIONS:
            jira_error.text = None
            jira_error.request = None
            jira_error.response = None
        super().__init__(message + ': ' + str(jira_error))


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
                      api: type = CrashServer, thread_count: int = 5, **options) -> List[str]:
    """Fetches :count new reports into :directory, which are not present in :known_reports and
    satisfy :min_version and :extension, returns created file names.
    """
    try:
        full_list = api(**options).list_all(extension=extension)
    except (CrashServerError, json.decoder.JSONDecodeError, IOError, OSError) as error:
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
        if isinstance(result, (CrashServerError, IOError, OSError)):
            logger.warning(utils.format_error(result))
        elif isinstance(result, Exception):
            logger.error(utils.format_error(result))
        else:
            downloaded.append(name)

    logger.info('Fetched {} new report(s)'.format(len(downloaded)))
    return downloaded


def _fetch_crash(name: str, directory: utils.Directory, api: type = CrashServer,
                 max_size: Union[int, str] = 0, **options) -> int:
    content = api(**options).get(name)
    size = utils.Size(len(content))
    if size > utils.Size(max_size):
        raise CrashServerError('Report of size {}B is too big: {}'.format(size, name))

    directory.file(name).write_bytes(content)
    return len(content)


class Jira:
    def __init__(self, url: str, login: str, password: str, file_limit: int, fix_versions: list, 
                 epic_link: str = '', prefix: str = ''):
        try:
            self._jira = jira.JIRA(server=url, basic_auth=(login, password))
        except jira.exceptions.JIRAError as error:
            raise JiraError('Unable to connect to {} with [{}:{}]'.format(url, login, password), error)

        self._file_limit = file_limit
        self._fix_versions = fix_versions
        self._epic_link = epic_link
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
                fixVersions=[{'name': v} for v in self._fix_versions_for(report.version)],
                components=[{'name': reason.component}],
                customfield_10200={"value": team(reason.component)},
                customfield_10009=self._epic_link,
                description='\n'.join(['Call Stack:', '{code}'] + reason.stack + ['{code}']))
        except jira.exceptions.JIRAError as error:
            raise JiraError('Unable to create issue for "{}"'.format(report.name), error)

        logger.info("New JIRA issue {}: {}".format(issue.key, issue.fields.summary))
        return issue.key

    def update_issue(self, key: str, reports: List[crash_info.Report], directory: utils.Directory) -> bool:
        """Update JIRA issue with new crash :reports.
        """
        logger.debug('Update JIRA issue {} with {}'.format(key, reports))
        if not reports:
            raise JiraError('Unable to update issue {} with no reports'.format(key))

        try:
            issue = self._jira.issue(key)
        except jira.exceptions.JIRAError as error:
            raise JiraError('Unable to update issue {}'.format(key), error)

        fix_build = issue.fields.customfield_11120
        if fix_build:
            reports = list(filter(lambda r: int(r.build) >= fix_build, reports))
            if not reports:
                return logger.debug('JIRA issue {} ignores new reports by fix build {}'.format(
                    key, fix_build))

        if issue.fields.status.name == 'Closed':
            if issue.fields.resolution.name == 'Rejected':
                return logger.debug('JIRA issue {} is rejected'.format(key))

            if not fix_build:
                min_fix_version = min(v.name for v in issue.fields.fixVersions)
                max_report_version = max(r.version for r in reports)
                if min_fix_version >= max_report_version:
                    return logger.debug('JIRA issue {} is already fixed'.format(key))

            if issue.fields.resolution.name != 'Duplicate':
                self._transition(issue, 'Reopen')
                logger.info('Reopen JIRA issue {} for reports from {}'.format(
                    key, ', '.join(r.full_version for r in reports)))
                
        versions = set()
        fix_versions = set()
        for r in reports:
            versions.add(r.version)
            fix_versions.update(self._fix_versions_for(r.version))
            files = directory.files(r.file_mask())
            if not files:
                raise JiraError('Unable to find files for {}'.format(r.name))
            self._attach_files(key, files)
            
        self._update_field_names(issue, 'versions', versions)
        self._update_field_names(issue, 'fixVersions', fix_versions, skip_on='Future')

    def all_issues(self):
        issues = []
        try:
            for issue in self._jira.search_issues('summary ~ "has crashed on"', maxResults=1000):
                summary = issue.fields.summary
                if summary.startswith(self._prefix) and 'has crashed on' in summary:
                    issues.append(issue)

        except jira.exceptions.JIRAError as error:
            raise JiraError('Unable to get all issues', error)

        return issues
    
    def _fix_versions_for(self, version):
        return set(v for v in self._fix_versions if v >= version)
        
    @staticmethod
    def _update_field_names(issue: jira.Issue, name: str, values: list, skip_on: str = ''):
        current_values = set(v.name for v in getattr(issue.fields, name))
        if skip_on and skip_on in current_values:
            logger.debug('JIRA issue {} update for {} is skipped on: {}'.format(
                issue.key, name, skip_on))
            return

        new_values = current_values | set(values)
        if current_values != new_values:
            issue.update(fields={name: [{'name': v} for v in new_values]})
            logger.debug('JIRA issue {} is updated for {}: {}'.format(
                issue.key, name, ', '.join(new_values)))
    
    def _attach_files(self, key: str, reports: List[utils.File]):
        """Attaches new :files to JIRA issue.
        """
        for report in reports[-self._file_limit:]:
            try:
                self._jira.add_attachment(key, attachment=report.path, filename=report.name)

            except jira.exceptions.JIRAError as jira_error:
                error = JiraError(
                    'Unable to attach "{}" file to issue {}'.format(report.name, key), jira_error)
                if jira_error.status_code == 413: #< HTTP Code: Payload Too Large.
                    logger.warning(utils.format_error(error))
                else:
                    raise error
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
            raise JiraError('Unable to cleanup attachments at issue {}'.format(key), error)

    def _transition(self, issue: jira.Issue, *transition_names: List[str], **kwargs: dict):
        for name in transition_names:
            try:
                for transition in self._jira.transitions(issue):
                    if transition['name'].startswith(name):
                        self._jira.transition_issue(issue, transition['id'], **kwargs)
                        continue

            except jira.exceptions.JIRAError as error:
                raise JiraError('Unable to transition issue {} to {}'.format(issue.key, name), error)

