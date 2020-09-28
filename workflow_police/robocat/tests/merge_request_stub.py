import gitlab
from dataclasses import dataclass, field

DEFAULT_COMMIT = {"sha": "11", "message": "msg1"}
COMMITS = dict()


@dataclass
class MergeRequestStub():
    approved: bool = True
    has_conflicts: bool = False
    blocking_discussions_resolved: bool = True
    needs_rebase: bool = False
    commits: bool = field(default_factory=lambda: {DEFAULT_COMMIT["sha"]: DEFAULT_COMMIT["message"]})
    pipelines_list: str = field(default_factory=lambda: [(DEFAULT_COMMIT["sha"], "success")])

    id: int = 7
    title: str = "Do Zorz at work"
    target_branch: str = "x/zorz_branch"
    merge_status: str = "can_be_merged"

    comments: list = field(default_factory=list, init=False)
    is_wip: bool = field(default=False, init=False)
    rebased: bool = field(default=False, init=False)
    merged: bool = field(default=False, init=False)

    def __post_init__(self):
        COMMITS.update(self.commits)

    def approvals_left(self):
        return 0 if self.approved else 1

    def last_commit(self):
        return next(iter(self.commits.items()), None)

    def pipelines(self):
        return [{"id": p[0], "sha": p[1][0], "status": p[1][1], "web_url": ""} for p in enumerate(self.pipelines_list)]

    def add_comment(self, title, message, emoji=""):
        self.comments.append((title, message, emoji))

    def set_wip(self):
        self.is_wip = True

    def rebase(self):
        self.rebased = True

    def merge(self):
        if self.needs_rebase:
            raise gitlab.exceptions.GitlabMRClosedError()
        self.merged = True

    def play_latest_pipeline(self):
        self.pipelines_list[0] = (self.pipelines_list[0][0], "running")
