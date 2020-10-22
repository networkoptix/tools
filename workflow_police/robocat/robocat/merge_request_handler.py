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

WATCH_EMOJI = "eyes"
WAIT_EMOJI = "hourglass_flowing_sand"
PIPELINE_EMOJI = "construction_site"
INITIAL_EMOJI = "cat2"


# TODO: Move out Reasons and make them storing their context and messages.
class ReturnToDevelopmentReason(enum.Enum):
    conflicts = enum.auto()
    failed_pipeline = enum.auto()
    unresolved_threads = enum.auto()


class RunPipelineReason(enum.Enum):
    """Reasons why pipeline run requested. The value is a description message"""
    no_pipelines_before = "making initial CI check"
    ci_errors_fixed = "checking if rebase fixed previous fails"
    review_finished = "checking new MR state"
    requested_by_user = "CI check requested by the user"


class WaitReason(enum.Enum):
    no_commits = "no commits in MR"
    not_approved = "not enough non-bot approvals"
    pipeline_running = "pipeline is in progress"


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


class MergeRequestHandler():
    def __init__(self, project):
        self._project = project

        self._pipelines_commits_count = {}

    # NOTE: required for lru_cache.
    def __hash__(self):
        return self._project.id

    def handle(self, mr):
        logger.debug(f"Handling MR {mr.id}: '{mr.title}'")

        if not mr.sha:
            return self.handle_wait(mr, WaitReason.no_commits)

        self.handle_award_emoji(mr)
        if mr.work_in_progress:
            mr.award_emoji.delete(WAIT_EMOJI, own=True)
            return

        if mr.has_conflicts:
            return self.return_to_development(mr, ReturnToDevelopmentReason.conflicts)

        approvals_left = mr.approvals_left()
        if approvals_left > 0:
            if not mr.has_conflicts and not mr.pipelines():
                return self.run_pipeline(mr, RunPipelineReason.no_pipelines_before)
            return self.handle_wait(mr, WaitReason.not_approved, approvals_left=approvals_left)

        last_pipeline = next((p for p in mr.pipelines() if p["status"] not in PIPELINE_STATUSES["skipped"]), None)
        inspection_result = self.inspect_pipeline(mr, last_pipeline)

        if inspection_result <= PipelineInspectionResult.hash_changed:
            return self.run_pipeline(mr, RunPipelineReason.review_finished, inspection_result)

        if last_pipeline["status"] in PIPELINE_STATUSES["running"]:
            return self.handle_wait(mr, WaitReason.pipeline_running, pipeline=last_pipeline)

        # NOTE: Let's check it only if pipeline was ran before.
        if not mr.blocking_discussions_resolved:
            return self.return_to_development(mr, ReturnToDevelopmentReason.unresolved_threads)

        if last_pipeline["status"] in PIPELINE_STATUSES["success"]:
            assert inspection_result >= PipelineInspectionResult.sha_changed
            return self.merge(mr)

        if last_pipeline["status"] in PIPELINE_STATUSES["failed"]:
            if inspection_result == PipelineInspectionResult.sha_changed:
                return self.run_pipeline(mr, RunPipelineReason.ci_errors_fixed)
            if inspection_result == PipelineInspectionResult.same_sha:
                return self.return_to_development(
                    mr, ReturnToDevelopmentReason.failed_pipeline,
                    pipeline_id=last_pipeline["id"], pipeline_url=last_pipeline["web_url"])
            assert False, f"Unexpected pipeline inspection result {inspection_result}"
        assert False, f"Unexpected status {last_pipeline['status']}"

    def inspect_pipeline(self, mr, pipeline):
        if pipeline is None:
            return PipelineInspectionResult.no_runs

        if pipeline["sha"] == mr.sha:
            return PipelineInspectionResult.same_sha

        if pipeline["id"] in self._pipelines_commits_count:
            if self._pipelines_commits_count[pipeline["id"]] != len(mr.commits()):
                return PipelineInspectionResult.commits_count_changed

        if self._get_commit_message(pipeline["sha"]) != self._get_commit_message(mr.sha):
            return PipelineInspectionResult.commit_message_changed

        if self._get_commit_diff_hash(pipeline["sha"]) != self._get_commit_diff_hash(mr.sha):
            return PipelineInspectionResult.hash_changed
        return PipelineInspectionResult.sha_changed

    def handle_award_emoji(cls, mr):
        if mr.award_emoji.find(PIPELINE_EMOJI, own=False):
            mr.award_emoji.delete(PIPELINE_EMOJI, own=False)
            cls.run_pipeline(mr, RunPipelineReason.requested_by_user)

        if not mr.award_emoji.find(WATCH_EMOJI, own=True):
            logger.info(f"{mr}: Found new merge request to take care of: {mr.title}")
            mr.award_emoji.create(WATCH_EMOJI)
            message = robocat.comments.initial_message.format(approvals_left=mr.approvals_left())
            mr.add_comment("Looking after this MR", message, f":{INITIAL_EMOJI}:")

    def handle_wait(cls, mr, reason, **kwargs):
        if mr.award_emoji.find(WAIT_EMOJI, own=True):
            logger.debug(f"{mr}: Ignored because {reason} and {WAIT_EMOJI} emoji is set")
            return

        if reason == WaitReason.no_commits:
            title = "Waiting for commits"
            message = robocat.comments.commits_wait_message
        elif reason == WaitReason.not_approved:
            title = "Waiting for approvals"
            message = robocat.comments.approval_wait_message.format(approvals_left=kwargs["approvals_left"])
        elif reason == WaitReason.pipeline_running:
            title = "Waiting for pipeline"
            message = robocat.comments.pipeline_wait_message.format(
                pipeline_id=kwargs["pipeline"]['id'], pipeline_url=kwargs["pipeline"]['web_url'])

        mr.award_emoji.create(WAIT_EMOJI)
        mr.add_comment(title, message, f":{WAIT_EMOJI}:")

    @classmethod
    def return_to_development(cls, mr, reason, **kwargs):
        logger.info(f"{mr}: Moving to WIP: {reason}")

        if reason == ReturnToDevelopmentReason.failed_pipeline:
            title = f"Pipeline [{kwargs['pipeline_id']}]({kwargs['pipeline_url']}) failed"
            message = robocat.comments.failed_pipeline_message
        elif reason == ReturnToDevelopmentReason.conflicts:
            title = "Conflicts with target branch"
            message = robocat.comments.conflicts_message
        elif reason == ReturnToDevelopmentReason.unresolved_threads:
            title = "Unresolved threads"
            message = robocat.comments.unresolved_threads_message
        else:
            assert False, f"Unknown reason: {reason}"

        mr.set_wip()
        mr.add_comment(title, message, ":exclamation:")
        mr.award_emoji.delete(WAIT_EMOJI, own=True)

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

        if reason == RunPipelineReason.review_finished:
            reason_msg = reason.value + ("" if not details else f" ({details})")
        else:
            reason_msg = reason.value

        message = robocat.comments.run_pipeline_message.format(pipeline_id=pipeline_id, reason=reason_msg)
        mr.add_comment("Pipeline started", message, f":{PIPELINE_EMOJI}:")
        mr.award_emoji.create(WAIT_EMOJI)

    # TODO: Create own commit entity?
    @lru_cache(maxsize=512)
    def _get_commit_message(self, sha):
        return self._project.commits.get(sha).message

    @lru_cache(maxsize=512)
    def _get_commit_diff_hash(self, sha):
        diff = self._project.commits.get(sha).diff()
        return hash(json.dumps(diff, sort_keys=True))
