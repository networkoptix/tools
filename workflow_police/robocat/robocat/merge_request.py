import robocat.comments

import logging

logger = logging.getLogger(__name__)


class AwardEmojiManager():
    def __init__(self, gitlab_award_emoji_manager, current_user, dry_run=False):
        self._gitlab_manager = gitlab_award_emoji_manager
        self._current_user = current_user
        self._dry_run = dry_run

    def list(self, own):
        if own:
            return [e for e in self._gitlab_manager.list(as_list=False) if e.user['username'] == self._current_user]
        else:
            return self._gitlab_manager.list()

    def find(self, name, own):
        return [e for e in self.list(own) if e.name == name]

    def create(self, name, **kwargs):
        logger.debug(f"Creating emoji {name}")
        if self._dry_run:
            return
        return self._gitlab_manager.create({'name': name}, **kwargs)

    def delete(self, name, own, **kwargs):
        logger.debug(f"Removing {name} emoji")
        if self._dry_run:
            return

        for emoji in self.find(name, own):
            self._gitlab_manager.delete(emoji.id, **kwargs)


class MergeRequest():
    def __init__(self, gitlab_mr, current_user, dry_run=False):
        self._gitlab_mr = gitlab_mr
        self._current_user = current_user
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
    def work_in_progress(self):
        return self._gitlab_mr.work_in_progress

    @property
    def award_emoji(self):
        return AwardEmojiManager(self._gitlab_mr.awardemojis, self._current_user, self._dry_run)

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
        pipeline_id = None
        if not self._dry_run:
            pipeline_id = project.pipelines.create({'ref': self._gitlab_mr.source_branch}).id
        logger.debug(f"Pipeline {pipeline_id} created for {self._gitlab_mr.source_branch}")
        return pipeline_id

    def _get_project(self, project_id):
        return self._gitlab_mr.manager.gitlab.projects.get(project_id, lazy=True)
