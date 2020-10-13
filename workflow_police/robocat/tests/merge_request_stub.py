import gitlab
from dataclasses import dataclass, field

DEFAULT_COMMIT = {"sha": "11", "message": "msg1"}
COMMITS = dict()


@dataclass
class AwardEmojiManager:
    emojis: field(default_factory=lambda: [])

    @dataclass
    class AwardEmoji:
        id: str = field(default=False)
        name: str = field(default=False)

    def delete(self, emoji_id):
        pass

    def list(self):
        return [self.AwardEmoji(e[0], e[1]) for e in enumerate(self.emojis)]

    def create(self, data):
        pass


@dataclass
class MergeRequestStub():
    approved: bool = True
    has_conflicts: bool = False
    blocking_discussions_resolved: bool = True
    needs_rebase: bool = False
    commits_list: dict = field(default_factory=lambda: {DEFAULT_COMMIT["sha"]: DEFAULT_COMMIT["message"]})
    pipelines_list: list = field(default_factory=lambda: [(DEFAULT_COMMIT["sha"], "success")])
    emojis: list = field(default_factory=list)

    id: int = 7
    title: str = "Do Zorz at work"
    target_branch: str = "x/zorz_branch"
    merge_status: str = "can_be_merged"

    comments: list = field(default_factory=list, init=False)
    is_wip: bool = field(default=False, init=False)
    rebased: bool = field(default=False, init=False)
    merged: bool = field(default=False, init=False)

    def __post_init__(self):
        COMMITS.update(self.commits_list)

    @property
    def award_emoji(self):
        return AwardEmojiManager(emojis=self.emojis)

    @property
    def sha(self):
        if not self.commits_list:
            return None
        return list(self.commits_list)[0]

    def commits(self):
        return list(self.commits_list)

    def approvals_left(self):
        return 0 if self.approved else 1

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

    def run_pipeline(self):
        self.pipelines_list.insert(0, (self.sha, "running"))
