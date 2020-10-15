import jira
import jira.exceptions

from collections import namedtuple
from typing import List, Dict
import logging
import datetime
import re

import police.utils


logger = logging.getLogger(__name__)


class JiraError(police.utils.Error):
    def __init__(self, message: str, jira_error: jira.exceptions.JIRAError = None):
        super().__init__(message + (': ' + str(jira_error) if jira_error else ""))


def branch_from_release(version: jira.resources.Version):
    if not hasattr(version, "description"):
        return None
    match = re.search(r"<(.+)>", version.description)
    if not match:
        return None
    return match.group(1)


def next_version_to_release(version_mapping: Dict):
    """First version mapped to master is considered to be a next version to release"""
    for version in version_mapping.keys():
        if version_mapping[version] == "master":
            return version


class JiraAccessor:
    project = "VMS"

    def __init__(self, url: str, login: str, password: str, timeout: int, retries: int):
        try:
            self._jira = jira.JIRA(server=url, basic_auth=(login, password), max_retries=retries, timeout=timeout)
        except jira.exceptions.JIRAError as error:
            raise JiraError(f"Unable to connect to {url} with {login}", error)

    def get_recently_closed_issues(self, period_min: int):
        issues_filter = (f'project = {self.project} '
                         f'AND (status = Closed AND resolved >= -{period_min}m '
                         f'OR status = "Waiting for QA" AND updated >= -{period_min}m)')
        logger.debug(f'Searching issues with filter [{issues_filter}]')
        return self._jira.search_issues(issues_filter, maxResults=None)

    def return_issue(self, issue: jira.Issue, reason: str, dry_run: bool):
        docs_link = "https://networkoptix.atlassian.net/wiki/spaces/SD/pages/1486749741/Automation+Workflow+Police+bot"

        try:
            logger.debug(f'Reopening issue {issue.key}: {reason}')
            if dry_run:
                return

            if issue.fields.status.name == "Closed":
                self._jira.transition_issue(issue, "Reopen")
            elif issue.fields.status.name == "Waiting for QA":
                self._jira.transition_issue(issue, "Back to Development")
            else:
                assert False, f"Unexpected issue {issue} status {issue.fields.status}"

            self._jira.add_comment(issue, (
                f"Workflow violation, issue returned: {reason}.\n"
                f"More info: [{docs_link}|{docs_link}|smart-link] \n\nh5. 🚔 Workflow Police"))

        except jira.exceptions.JIRAError as error:
            raise JiraError(f"Unable to reopen issue {issue.key}: {error}")

    @police.utils.cached(datetime.timedelta(minutes=10))
    def version_to_branch_mapping(self):
        try:
            mapping = {}
            for v in self._jira.project_versions(self.project):
                if v.archived:
                    continue
                branch = branch_from_release(v)
                if not branch:
                    logger.warning(f"Version {v.name} doesn't have branch in description")
                else:
                    mapping[v.name] = branch

            mapping = {k: mapping[k] for k in sorted(mapping)}
            logger.debug(f"Got mapping from jira releases: {mapping}")
            return mapping
        except jira.exceptions.JIRAError as error:
            raise JiraError(f"Unable to get release versions", error)
