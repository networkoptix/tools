import robocat.comments
import logging
import gitlab

import time
import enum
from functools import lru_cache

logger = logging.getLogger(__name__)


PIPELINE_STATUSES = {
    "skipped": ["canceled", "skipped", "created", "manual"],
    "running": ["waiting_for_resource", "preparing", "pending", "running", "scheduled"],
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
    def blocking_discussions_resolved(self):
        return self._gitlab_mr.blocking_discussions_resolved

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
        project = self._get_project(self._gitlab_mr.project_id)
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

    def run_pipeline(self):
        project = self._get_project(self._gitlab_mr.source_project_id)
        # TODO: should be changed to detached pipeline once gitlab API supports it
        pipeline = project.pipelines.create({'ref': self._gitlab_mr.source_branch})
        logger.debug(f"Pipeline {pipeline.id} created for {self._gitlab_mr.source_branch}")
        return pipeline.id

    def _get_project(self, project_id):
        return self._gitlab_mr.manager.gitlab.projects.get(project_id, lazy=True)


class MergeRequestHandler():
    class ReturnToDevelopmentReason(enum.Enum):
        conflicts = enum.auto()
        failed_pipeline = enum.auto()
        unresolved_threads = enum.auto()

    class RunPipelineReason(enum.Enum):
        no_pipelines_before = enum.auto()
        ci_errors_fixed = enum.auto()
        review_finished = enum.auto()

    def __init__(self, project):
        self._project = project

    def handle(self, mr):
        logger.debug(f"Handling MR {mr.id}: '{mr.title}'")

        last_commit = mr.last_commit()
        if not last_commit:
            return "no commits in MR"

        if mr.has_conflicts:
            self.return_to_development(mr, self.ReturnToDevelopmentReason.conflicts)
            return

        approvals_left = mr.approvals_left()
        if approvals_left > 0:
            if not mr.has_conflicts and not mr.pipelines():
                self.run_pipeline(mr, self.RunPipelineReason.no_pipelines_before)
                return

            return f"not enough non-bot approvals, {approvals_left} more required"

        # NOTE: Comparing by commit message, because SHA changes after rebase.
        last_pipeline = next((p for p in mr.pipelines() if self._get_commit_message(p["sha"]) == last_commit[1]), None)
        if last_pipeline is None or last_pipeline["status"] in PIPELINE_STATUSES["skipped"]:
            self.run_pipeline(mr, self.RunPipelineReason.review_finished)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["running"]:
            return f'pipeline {last_pipeline["id"]} (status: {last_pipeline["status"]}) is in progress'

        # NOTE: Let's check it only if pipeline was ran before.
        if not mr.blocking_discussions_resolved:
            self.return_to_development(mr, self.ReturnToDevelopmentReason.unresolved_threads)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["success"]:
            self.merge(mr)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["failed"]:
            if last_pipeline["sha"] == last_commit[0]:
                self.return_to_development(mr, self.ReturnToDevelopmentReason.failed_pipeline,
                                           pipeline_id=last_pipeline["id"],
                                           pipeline_url=last_pipeline["web_url"])
            else:
                self.run_pipeline(mr, self.RunPipelineReason.ci_errors_fixed)
            return

        assert False, f"Unexpected status {last_pipeline['status']}"

    @classmethod
    def return_to_development(cls, mr, reason, **kwargs):
        logger.info(f"MR!{mr.id}: moving to WIP: {reason}")

        if reason == cls.ReturnToDevelopmentReason.failed_pipeline:
            title = f"Pipeline [{kwargs['pipeline_id']}]({kwargs['pipeline_url']}) failed"
            message = robocat.comments.failed_pipeline_message
        elif reason == cls.ReturnToDevelopmentReason.conflicts:
            title = "Conflicts with target branch"
            message = robocat.comments.conflicts_message
        elif reason == cls.ReturnToDevelopmentReason.unresolved_threads:
            title = "Unresolved threads"
            message = robocat.comments.unresolved_threads_message
        else:
            assert False, f"Uknown reason: {reason}"

        mr.set_wip()
        mr.add_comment(title, message, ":exclamation:")

    # TODO: should approve here and add emoji to MR
    @classmethod
    def merge(cls, mr):
        try:
            logger.info(f"{mr}: merging or rebasing")
            mr.merge()
            message = robocat.comments.merged_message.format(branch=mr.target_branch)
            mr.add_comment("MR merged", message, ":white_check_mark:")
        except gitlab.exceptions.GitlabMRClosedError as e:
            # NOTE: gitlab API sucks and there is no other way to know if rebase required.
            logger.info(f"Got error during merge, most probably just rebase required: {e}")
            mr.rebase()

    @classmethod
    def run_pipeline(cls, mr, reason):
        logger.info(f"{mr}: running latest pipeline")
        pipeline_id = mr.run_pipeline()

        if reason == cls.RunPipelineReason.ci_errors_fixed:
            reason_msg = "checking if rebase fixed previous fails"
        elif reason == cls.RunPipelineReason.review_finished:
            reason_msg = "checking last commit state"
        elif reason == cls.RunPipelineReason.no_pipelines_before:
            reason_msg = "making preliminary CI check"
        else:
            assert False, f"Uknown reason: {reason}"

        message = robocat.comments.run_pipeline_message.format(pipeline_id=pipeline_id, reason=reason_msg)
        mr.add_comment("Pipeline started", message, ":construction_site:")

    # TODO: suboptimal! should use common cache for all MRs
    @lru_cache(maxsize=512)
    def _get_commit_message(self, sha):
        return self._project.commits.get(sha).message
