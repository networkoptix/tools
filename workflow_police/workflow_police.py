#!/usr/bin/env python3

import git
import jira
import graypy

from pathlib import Path
from typing import List, Dict, Tuple, Optional

import time
import datetime
import logging
import argparse
import sys

import utils
from jira_tools import JiraAccessor, JiraError


logger = logging.getLogger(__name__)

IGNORE_LABEL = "hide_from_police"
VERSION_SPECIFIC_LABEL = "version_specific"
DONE_EXTERNALLY_LABEL = "done_externally"


class RepoAccessor():
    def __init__(self, path: Path, url: str):
        try:
            self.repo = git.Repo(path)
        except git.exc.NoSuchPathError as e:
            self.repo = git.Repo.clone_from(url, path)

    def update_repository(self):
        self.repo.remotes.origin.fetch()

    def grep_recent_commits(self, substring: str, branch: str) -> List:
        return list(self.repo.iter_commits(f"origin/{branch}", grep=substring, since='18 month ago'))


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
                logger.warning(f"Checker for {issue.name} failed with error: {error}")
        return None


class WrongVersionChecker:
    class Version:
        def __init__(self, jira_version: str):
            version_splitted = jira_version.split('_')
            assert len(version_splitted) == 2 and version_splitted[1] == "patch" or len(version_splitted) == 1
            self.number = version_splitted[0]
            self.is_patch = len(version_splitted) == 2

        def __gt__(self, other):
            return (self.number, self.is_patch) > (other.number, other.is_patch)

        def __repr__(self):
            return self.number + ("_patch" if self.is_patch else "")

    def __init__(self, jira_accessor: JiraAccessor):
        self._jira = jira_accessor

    def __call__(self, issue: jira.Issue) -> Optional[str]:
        if VERSION_SPECIFIC_LABEL in issue.fields.labels:
            return

        versions = sorted([self.Version(v.name) for v in issue.fields.fixVersions], reverse=True)
        if self.Version("Future") in versions and len(versions) > 1:
            return f"wrong fixVersions field value, 'Future' can't be set along with other versions"

        if sum(not v.is_patch for v in versions) != 1:
            return f"wrong fixVersions field value, exactly one release version required"

        if versions[0].is_patch:
            return f"wrong fixVersions field value, major version [{versions[0]}] shouldn't be a patch"

        # NOTE: A string with versions without gaps. E.g. 'Future 4.3 4.2 4.1 4.0'
        versions_sequence = " ".join(sorted(
            {self.Version(v).number for v in self._jira.version_to_branch_mapping().keys()}, reverse=True))
        if " ".join(sorted({v.number for v in versions}, reverse=True)) not in versions_sequence:
            return f"wrong fixVersions field value, there shouldn't be gaps between versions"

        return


class VersionMissingIssueCommitChecker:
    def __init__(self, jira_accessor: JiraAccessor, repo: RepoAccessor):
        self._jira = jira_accessor
        self._repo = repo

    def __call__(self, issue: jira.Issue) -> Optional[str]:
        for version in issue.fields.fixVersions:
            # NOTE: checking only recent commits as an optimization
            branch = self._jira.version_to_branch_mapping()[version.name]
            if len(self._repo.grep_recent_commits(issue.key, branch)) == 0:
                return f"no commits in {version.name} version (branch: {branch})"
        return


class MasterMissingIssueCommitChecker:
    def __init__(self, repo: RepoAccessor):
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


class WorkflowEnforcer:
    def __init__(self, config: Dict, dry_run: bool):
        self._polling_period_min = config["polling_period_min"]
        self._last_check_file = config["last_check_file"]

        self.dry_run = dry_run

        self._jira = JiraAccessor(**config["jira"])
        self._repo = RepoAccessor(**config["repo"])

        self._workflow_checker = WorkflowViolationChecker()
        self._workflow_checker.register_ignore_checker(
            lambda i: f"{IGNORE_LABEL} is set" if IGNORE_LABEL in i.fields.labels else None)
        self._workflow_checker.register_ignore_checker(check_issue_type)
        self._workflow_checker.register_ignore_checker(check_issue_not_fixed)

        self._workflow_checker.register_reopen_checker(WrongVersionChecker(self._jira))
        self._workflow_checker.register_reopen_checker(VersionMissingIssueCommitChecker(self._jira, self._repo))
        self._workflow_checker.register_reopen_checker(MasterMissingIssueCommitChecker(self._repo))

    def get_recent_issues_interval_min(self):
        try:
            with open(self._last_check_file, "r") as f:
                last_check_timestamp = int(f.read())
                now = int(datetime.datetime.now().timestamp())
                return (now - last_check_timestamp) // 60 + self._polling_period_min
        except FileNotFoundError:
            logger.info(f"No previous runs detected, using {self._polling_period_min * 2} min period")
            return self._polling_period_min * 2

    def update_last_check_timestamp(self):
        if self.dry_run:
            logger.debug(f"Skipping update of {self._last_check_file} (dry-run)")
            return

        with open(self._last_check_file, "w") as f:
            f.write(str(int(datetime.datetime.now().timestamp())))

    def run(self):
        while True:
            recent_issues_interval_min = self.get_recent_issues_interval_min()
            logger.info(f"Verifying issues updated for last {recent_issues_interval_min} minutes")
            issues = self._jira.get_recently_closed_issues(recent_issues_interval_min)
            self._repo.update_repository()

            for issue in issues:
                reason = self._workflow_checker.should_ignore_issue(issue)
                if reason:
                    logger.debug(f"Ignoring {issue}: {reason}")
                    continue
                logger.debug(f"Checking issue: {issue} ({issue.fields.status}) "
                             f"with versions {[v.name for v in issue.fields.fixVersions]}")
                reason = self._workflow_checker.should_reopen_issue(issue)
                if not reason:
                    continue
                self._jira.return_issue(issue, reason, self.dry_run)

            logger.info(f"All {len(issues)} issues handled")
            self.update_last_check_timestamp()

            if self.dry_run:
                return
            time.sleep(self._polling_period_min * 60)


def main():
    parser = argparse.ArgumentParser("workflow_police")
    parser.add_argument('config_file', help="Config file with all options")
    parser.add_argument('--log-level', help="Logs level", choices=logging._nameToLevel.keys(), default=logging.INFO)
    parser.add_argument('--dry-run', help="Run single iteration, don't change any states", action="store_true")
    parser.add_argument('--graylog', help="Hostname of Graylog service")
    arguments = parser.parse_args()

    logging.basicConfig(
        level=arguments.log_level,
        format='%(asctime)s %(levelname)s %(name)s\t%(message)s')
    if arguments.graylog:
        logging.getLogger().addHandler(graypy.GELFTCPHandler(arguments.graylog, level_names=True))
        logger.debug(f"Logging to Graylog at {arguments.graylog}")

    try:
        config = utils.parse_config_file(Path(arguments.config_file))
        enforcer = WorkflowEnforcer(config, arguments.dry_run)
        enforcer.run()
    except Exception as e:
        logger.warning(f'Crashed with exception: {e}', exc_info=1)
        sys.exit(1)


if __name__ == '__main__':
    main()
