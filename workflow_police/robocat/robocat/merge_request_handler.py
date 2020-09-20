import robocat.comments
import logging
import gitlab

import time
import enum
from functools import lru_cache

logger = logging.getLogger(__name__)


PIPELINE_STATUSES = {
    "skipped": ["canceled", "skipped", "created"],
    "running": ["waiting_for_resource", "preparing", "pending", "running", "scheduled", "manual"],
    "success": ["success"],
    "failed": ["failed"]
}


class MergeRequest():
    def __init__(self, gitlab_mr, dry_run=False):
        self._gitlab_mr = gitlab_mr
        self._dry_run = dry_run

    def __str__(self):
        return f"MR!{self.id}"

    @property
    def id(self):
        return self._gitlab_mr.iid

    @property
    def title(self):
        return self._gitlab_mr.title

    @property
    def target_branch(self):
        return self._gitlab_mr.target_branch

    def approvals_left(self):
        approvals = self._gitlab_mr.approvals.get()
        return approvals.approvals_left  # TODO: should be remove once approval logic is fully implemented.

        if approvals.approvals_left == 0:
            return 0

        if approvals.user_can_approve and not approvals.user_has_approved:
            return approvals.approvals_left - 1
        return approvals.approvals_left

    @property
    def has_conflicts(self):
        return self._gitlab_mr.has_conflicts

    @property
    def merge_status(self):
        return self._gitlab_mr.merge_status

    def last_commit(self):
        last_commit = next(self._gitlab_mr.commits(), None)
        if not last_commit:
            return None
        return (last_commit.id, last_commit.message)

    def pipelines(self):
        return self._gitlab_mr.pipelines()

    def add_comment(self, title, message, emoji=""):
        logger.debug(f"{self}: Adding comment with title: {title}")
        if not self._dry_run:
            self._gitlab_mr.notes.create({'body':  robocat.comments.template.format(**locals())})

    def set_wip(self):
        logger.debug(f"{self}: Set WIP")
        if not self._dry_run:
            self._gitlab_mr.notes.create({'body': "/wip"})

    def refetch(self, include_rebase_in_progress=False):
        project = self._get_project()
        self._gitlab_mr = project.mergerequests.get(self.id, include_rebase_in_progress=include_rebase_in_progress)

    def rebase(self):
        logger.debug(f"{self}: Rebasing")
        if self._dry_run:
            return False
        self._gitlab_mr.rebase()

    def merge(self):
        logger.debug(f"{self}: Merging")
        if self._dry_run:
            return

        squash_commit_message = None
        if self._gitlab_mr.squash:
            squash_commit_message = f"{self._gitlab_mr.title}\n\n{self._gitlab_mr.description}"
        self._gitlab_mr.merge(squash_commit_message=squash_commit_message)

    def play_latest_pipeline(self):
        project = self._get_project()
        latest_pipeline_id = max(p['id'] for p in self.pipelines())
        latest_pipeline = project.pipelines.get(latest_pipeline_id, lazy=True)

        logger.info(f"{self}: Playing pipeline {latest_pipeline_id}")
        if not self._dry_run:
            for job in latest_pipeline.jobs.list():
                if job.status == "manual":
                    project.jobs.get(job.id, lazy=True).play()
        return latest_pipeline_id

    def _get_project(self):
        return self._gitlab_mr.manager.gitlab.projects.get(self._gitlab_mr.project_id, lazy=True)


class MergeRequestHandler():
    class ReturnToDevelopmentReason(enum.Enum):
        conflicts = enum.auto()
        failed_pipeline = enum.auto()

    def __init__(self, project):
        self._project = project

    def handle(self, mr):
        logger.debug(f"Handling MR {mr.id}: '{mr.title}'")

        approvals_left = mr.approvals_left()
        if approvals_left > 0:
            return f"not enough non-bot approvals, {approvals_left} more required"

        if mr.has_conflicts:
            self.return_to_development(mr, self.ReturnToDevelopmentReason.conflicts)
            return

        last_commit = mr.last_commit()
        if not last_commit:
            return "no commits in MR"

        # NOTE: Comparing by commit message, because SHA changes after rebase.
        last_commit_pipelines = (
            p for p in mr.pipelines() if self._get_commit_message(p["sha"]) == last_commit[1])
        last_ran_pipeline = next(
            (p for p in last_commit_pipelines if p["status"] not in PIPELINE_STATUSES["skipped"]), None)

        if last_ran_pipeline is None:
            self.run_pipeline(mr)
            return

        if last_ran_pipeline["status"] in PIPELINE_STATUSES["running"]:
            return f'pipeline {last_ran_pipeline["id"]} (status: {last_ran_pipeline["status"]}) is in progress'

        if last_ran_pipeline["status"] in PIPELINE_STATUSES["success"]:
            self.merge(mr)
            return

        if last_ran_pipeline["status"] in PIPELINE_STATUSES["failed"]:
            if last_ran_pipeline["sha"] == last_commit[0]:
                self.return_to_development(mr, self.ReturnToDevelopmentReason.failed_pipeline)
            else:
                self.run_pipeline(mr)  # NOTE: pipeline might be fixed after rebase
            return

        assert False, f"Unexpected status {last_ran_pipeline['status']}"

    @classmethod
    def return_to_development(cls, mr, reason):
        logger.info(f"MR!{mr.id}: moving to WIP: {reason}")
        if reason == cls.ReturnToDevelopmentReason.failed_pipeline:
            title = "Failed pipeline"
            message = robocat.comments.failed_pipeline_message
        elif reason == cls.ReturnToDevelopmentReason.conflicts:
            title = "Conflicts with target branch"
            message = robocat.comments.conflicts_message
        else:
            assert False, f"Uknown reason: {reason}"

        mr.set_wip()
        mr.add_comment(title, message, ":exclamation:")

    # TODO: should approve here and add emoji to MR
    @classmethod
    def merge(cls, mr):
        try:
            logger.info(f"{mr}: rebasing and merging")
            mr.merge()
            message = robocat.comments.merged_message.format(branch=mr.target_branch)
            mr.add_comment("MR merged", message, ":white_check_mark:")
        except gitlab.exceptions.GitlabMRClosedError as e:
            # NOTE: gitlab API sucks and there is no other way to know if rebase required.
            logger.info(f"Got error during merge, most probably just rebase required: {e}")
            mr.rebase()

    @classmethod
    def run_pipeline(cls, mr):
        logger.info(f"{mr}: running latest pipeline")

        pipeline_id = mr.play_latest_pipeline()
        message = robocat.comments.run_pipeline_message.format(pipeline=pipeline_id)
        mr.add_comment("Pipeline started", message, ":construction_site:")

    @lru_cache(maxsize=512)
    def _get_commit_message(self, sha):
        return self._project.commits.get(sha).message
