import jira

from typing import List, Dict, Tuple, Optional
import logging

import police.utils
from police.jira_tools import JiraAccessor, JiraError


logger = logging.getLogger(__name__)

IGNORE_LABEL = "hide_from_police"
VERSION_SPECIFIC_LABEL = "version_specific"
DONE_EXTERNALLY_LABEL = "done_externally"


class WorkflowViolationChecker:
    def __init__(self):
        self.reopen_checkers = []
        self.ignore_checkers = []

    def register_reopen_checker(self, checker):
        self.reopen_checkers.append(checker)

    def register_ignore_checker(self, checker):
        self.ignore_checkers.append(checker)

    def should_ignore_issue(self, issue: jira.Issue) -> Optional[str]:
        return self._run_checkers(issue, self.ignore_checkers)

    def should_reopen_issue(self, issue: jira.Issue) -> Optional[str]:
        return self._run_checkers(issue, self.reopen_checkers)

    @staticmethod
    def _run_checkers(issue: jira.Issue, checkers: List) -> Optional[str]:
        for checker in checkers:
            try:
                reason = checker(issue)
                if reason:
                    return reason
            except Exception as error:
                logger.error(f"Checker for {issue.name} failed with error: {error}")
        return None


class WrongVersionChecker:
    def __init__(self, jira_accessor: JiraAccessor):
        self._jira = jira_accessor

    def __call__(self, issue: jira.Issue) -> Optional[str]:
        if VERSION_SPECIFIC_LABEL in issue.fields.labels:
            return

        versions = sorted([police.utils.Version(v.name) for v in issue.fields.fixVersions], reverse=True)
        if police.utils.Version("Future") in versions and len(versions) > 1:
            return f"wrong fixVersions field value, 'Future' can't be set along with other versions"

        if sum(not v.is_patch for v in versions) != 1:
            return f"wrong fixVersions field value, exactly one release version required"

        if versions[0].is_patch:
            return f"wrong fixVersions field value, major version [{versions[0]}] shouldn't be a patch"

        # NOTE: A string with versions (not counting patches) without gaps. E.g. 'Future 4.3 4.2 4.1 4.0'
        versions_sequence = " ".join(v.number for v in self._jira.version_to_branch_mapping().keys() if not v.is_patch)
        if " ".join(v.number for v in versions) not in versions_sequence:
            return f"wrong fixVersions field value, there shouldn't be gaps between versions"

        return


class VersionMissingIssueCommitChecker:
    def __init__(self, jira_accessor: JiraAccessor, repo: police.utils.RepoAccessor):
        self._jira = jira_accessor
        self._repo = repo

    def __call__(self, issue: jira.Issue) -> Optional[str]:
        for version in issue.fields.fixVersions:
            # NOTE: checking only recent commits as an optimization
            branch = self._jira.version_to_branch_mapping()[police.utils.Version(version.name)]
            if len(self._repo.grep_recent_commits(issue.key, branch)) == 0:
                return f"no commits in {version.name} version (branch: {branch})"
        return


class MasterMissingIssueCommitChecker:
    def __init__(self, repo: police.utils.RepoAccessor):
        self._repo = repo

    def __call__(self, issue: jira.Issue) -> Optional[str]:
        if VERSION_SPECIFIC_LABEL in issue.fields.labels:
            return
        if len(self._repo.grep_recent_commits(issue.key, "master")) == 0:
            return f"no commits in master"


def check_issue_type(issue: jira.Issue) -> Optional[str]:
    if issue.fields.issuetype.name in ["New Feature", "Epic", "Func Spec", "Tech Spec"]:
        return f"issue type [{issue.fields.issuetype}]"
    return


def check_issue_not_fixed(issue: jira.Issue) -> Optional[str]:
    if issue.fields.status.name == "Waiting for QA" and DONE_EXTERNALLY_LABEL not in issue.fields.labels:
        return
    if str(issue.fields.resolution) in ["Fixed", "Done"]:
        return
    return f"issue resolution [{issue.fields.resolution}], issue status [{issue.fields.status}]"
