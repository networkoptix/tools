import robocat.comments

import logging
import gitlab

import json
import time
import enum
from functools import lru_cache, total_ordering

logger = logging.getLogger(__name__)


PIPELINE_STATUSES = {
    "skipped": ["canceled", "skipped", "created", "manual"],
    "running": ["waiting_for_resource", "preparing", "pending", "running", "scheduled"],
    "success": ["success"],
    "failed": ["failed"]
}


class MergeRequestHandler():
    class ReturnToDevelopmentReason(enum.Enum):
        conflicts = enum.auto()
        failed_pipeline = enum.auto()
        unresolved_threads = enum.auto()

    class RunPipelineReason(enum.Enum):
        """Reasons why pipeline run requested. The value is a description message"""
        no_pipelines_before = "making preliminary CI check"
        ci_errors_fixed = "checking if rebase fixed previous fails"
        review_finished = "checking new MR state"
        requested_by_user = "CI check requested by user"

    @total_ordering
    class PipelineInspectionResult(enum.Enum):
        no_runs = (1, "no ran pipelines before")
        commits_count_changed = (2, "commits count changed")
        commit_message_changed = (3, "last commit name changed")
        hash_changed = (4, "commit diff changed")
        sha_changed = (5, "commit sha changed")
        same_sha = (6, "nothing changed")

        def __str__(self):
            return self.value[1]

        def __eq__(self, other):
            return other.value[0] == self.value[0]

        def __lt__(self, other):
            return self.value[0] < other.value[0]

    def __init__(self, project):
        self._project = project

        self._pipelines_commits_count = {}

    # NOTE: required for lru_cache.
    def __hash__(self):
        return self._project.id

    def handle(self, mr):
        logger.debug(f"Handling MR {mr.id}: '{mr.title}'")

        if not mr.sha:
            return "no commits in MR"

        self.handle_award_emoji(mr)

        if mr.has_conflicts:
            self.return_to_development(mr, self.ReturnToDevelopmentReason.conflicts)
            return

        approvals_left = mr.approvals_left()
        if approvals_left > 0:
            if not mr.has_conflicts and not mr.pipelines():
                self.run_pipeline(mr, self.RunPipelineReason.no_pipelines_before)
                return

            return f"not enough non-bot approvals, {approvals_left} more required"

        last_pipeline = next((p for p in mr.pipelines() if p["status"] not in PIPELINE_STATUSES["skipped"]), None)
        inspection_result = self.inspect_pipeline(mr, last_pipeline)

        if inspection_result <= self.PipelineInspectionResult.hash_changed:
            self.run_pipeline(mr, self.RunPipelineReason.review_finished, inspection_result)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["running"]:
            return f'pipeline {last_pipeline["id"]} (status: {last_pipeline["status"]}) is in progress'

        # NOTE: Let's check it only if pipeline was ran before.
        if not mr.blocking_discussions_resolved:
            self.return_to_development(mr, self.ReturnToDevelopmentReason.unresolved_threads)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["success"]:
            assert inspection_result >= self.PipelineInspectionResult.sha_changed
            self.merge(mr)
            return

        if last_pipeline["status"] in PIPELINE_STATUSES["failed"]:
            if inspection_result == self.PipelineInspectionResult.sha_changed:
                self.run_pipeline(mr, self.RunPipelineReason.ci_errors_fixed)
                return
            if inspection_result == self.PipelineInspectionResult.same_sha:
                self.return_to_development(
                    mr, self.ReturnToDevelopmentReason.failed_pipeline,
                    pipeline_id=last_pipeline["id"], pipeline_url=last_pipeline["web_url"])
                return
            assert False, f"Unexpected pipeline inspection result {inspection_result}"
        assert False, f"Unexpected status {last_pipeline['status']}"

    def inspect_pipeline(self, mr, pipeline):
        if pipeline is None:
            return self.PipelineInspectionResult.no_runs

        if pipeline["sha"] == mr.sha:
            return self.PipelineInspectionResult.same_sha

        if pipeline["id"] in self._pipelines_commits_count:
            if self._pipelines_commits_count[pipeline["id"]] != len(mr.commits()):
                return self.PipelineInspectionResult.commits_count_changed

        if self._get_commit_message(pipeline["sha"]) != self._get_commit_message(mr.sha):
            return self.PipelineInspectionResult.commit_message_changed

        if self._get_commit_diff_hash(pipeline["sha"]) != self._get_commit_diff_hash(mr.sha):
            return self.PipelineInspectionResult.hash_changed
        return self.PipelineInspectionResult.sha_changed

    def handle_award_emoji(cls, mr):
        emojis = mr.award_emoji.list()
        if "construction_site" in (e.name for e in emojis):
            cls.run_pipeline(mr, cls.RunPipelineReason.requested_by_user)
            for emoji_id in (e.id for e in emojis if e.name == "construction_site"):
                mr.award_emoji.delete(emoji_id)

        if "eyes" not in (e.name for e in emojis):
            mr.award_emoji.create({'name': 'eyes'})
            logger.info(f"{mr}: Found new merge request to take care of: {mr.title}")

    @classmethod
    def return_to_development(cls, mr, reason, **kwargs):
        logger.info(f"{mr}: Moving to WIP: {reason}")

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
            assert False, f"Unknown reason: {reason}"

        mr.set_wip()
        mr.add_comment(title, message, ":exclamation:")

    # TODO: should approve here and add emoji to MR
    @classmethod
    def merge(cls, mr):
        try:
            logger.info(f"{mr}: Merging or rebasing")
            mr.merge()
            message = robocat.comments.merged_message.format(branch=mr.target_branch)
            mr.add_comment("MR merged", message, ":white_check_mark:")
        except gitlab.exceptions.GitlabMRClosedError as e:
            # NOTE: gitlab API sucks and there is no other way to know if rebase required.
            logger.info(f"{mr}: Got error during merge, most probably just rebase required: {e}")
            mr.rebase()

    def run_pipeline(self, mr, reason, details=None):
        logger.info(f"{mr}: Running pipeline ({reason})")
        pipeline_id = mr.run_pipeline()
        self._pipelines_commits_count[pipeline_id] = len(mr.commits())

        if reason == self.RunPipelineReason.review_finished:
            reason_msg = reason.value + ("" if not details else f" ({details})")
        else:
            reason_msg = reason.value

        message = robocat.comments.run_pipeline_message.format(pipeline_id=pipeline_id, reason=reason_msg)
        mr.add_comment("Pipeline started", message, ":construction_site:")

    # TODO: Create own commit entity?
    @lru_cache(maxsize=512)
    def _get_commit_message(self, sha):
        return self._project.commits.get(sha).message

    @lru_cache(maxsize=512)
    def _get_commit_diff_hash(self, sha):
        diff = self._project.commits.get(sha).diff()
        return hash(json.dumps(diff, sort_keys=True))
