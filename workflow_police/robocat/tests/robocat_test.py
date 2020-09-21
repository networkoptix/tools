import pytest

import gitlab
from dataclasses import dataclass, field

import robocat.merge_request_handler


DEFAULT_COMMIT = {"sha": "11", "message": "msg1"}
COMMITS = dict()


@dataclass
class MergeRequestStub():
    approved: bool = True
    has_conflicts: bool = False
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
        return [{"id": p[0], "sha": p[1][0], "status": p[1][1]} for p in enumerate(self.pipelines_list)]

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


@pytest.fixture
def mr_handler(monkeypatch):
    handler = robocat.merge_request_handler.MergeRequestHandler(None)

    def stub_get_commit_message(sha):
        return COMMITS[sha]

    monkeypatch.setattr(handler, "_get_commit_message", stub_get_commit_message)
    return handler


testdata = [
    (
        # MR not approved: -> nothing changed
        {"approved": False},
        {"pipeline_status": "success"}),
    (
        # MR has conflicts -> wip, comment
        {"has_conflicts": True},
        {"actions": ["wip"], "comments": 1, "pipeline_status": "success"}),
    (
        # MR don't have commits -> nothing changed
        {"commits": {}},
        {"pipeline_status": "success"}),
    (
        # Pipeline in progress -> nothing changed
        {"pipelines_list": [(DEFAULT_COMMIT["sha"], "running")]},
        {"pipeline_status": "running"}),
    (
        # No pipelines, needs rebase -> pipeline started, comment
        {"needs_rebase": True, "pipelines_list": [(DEFAULT_COMMIT["sha"], "skipped")]},
        {"comments": 1, "pipeline_status": "running"}),
    (
        # No pipelines, no conflicts -> pipeline started, comment
        {"pipelines_list": [(DEFAULT_COMMIT["sha"], "skipped")]},
        {"comments": 1, "pipeline_status": "running"}),
    (
        # Pipeline successfull, needs rebase -> rebased, not merged
        {"needs_rebase": True},
        {"actions": ["rebased"], "pipeline_status": "success"}),
    (
        # Pipeline successfull, no conflicts -> merged, comment
        {},
        {"actions": ["merged"], "comments": 1, "pipeline_status": "success"}),
    (
        # Pipeline failed -> wip, comment
        {"commits": {"11": "same_msg", "22": "same_msg"}, "pipelines_list": [("11", "failed"), ("22", "skipped")]},
        {"actions": ["wip"], "comments": 1, "pipeline_status": "failed"}),
    (
        # Pipeline with old sha failed -> pipeline started, comment
        {"commits": {"11": "same_msg", "22": "same_msg"}, "pipelines_list": [("11", "skipped"), ("22", "failed")]},
        {"comments": 1, "pipeline_status": "running"})
]


@pytest.mark.parametrize("mr_state,expected_state", testdata)
def test_merge_request_handler(mr_handler, mr_state, expected_state):
    mr = MergeRequestStub(**mr_state)
    mr_handler.handle(mr)
    assert ("wip" in expected_state.get("actions", [])) == mr.is_wip
    assert ("rebased" in expected_state.get("actions", [])) == mr.rebased
    assert ("merged" in expected_state.get("actions", [])) == mr.merged
    assert expected_state.get("comments", 0) == len(mr.comments)
    assert expected_state["pipeline_status"] == mr.pipelines_list[0][1]
