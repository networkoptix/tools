import robocat.comments

import logging

logger = logging.getLogger(__name__)


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

    @property
    def award_emoji(self):
        return self._gitlab_mr.awardemojis

    def approvals_left(self):
        approvals = self._gitlab_mr.approvals.get()
        return approvals.approvals_left  # TODO: should be removed once approval logic is fully implemented.

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

    @property
    def sha(self):
        return self._gitlab_mr.sha

    def commits(self):
        return [commit.id for commit in self._gitlab_mr.commits()]

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
        if not self._dry_run:
            pipeline_id = project.pipelines.create({'ref': self._gitlab_mr.source_branch}).id
        logger.debug(f"Pipeline {pipeline_id} created for {self._gitlab_mr.source_branch}")
        return pipeline_id

    def _get_project(self, project_id):
        return self._gitlab_mr.manager.gitlab.projects.get(project_id, lazy=True)
