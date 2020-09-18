import pytest

import gitlab
from dataclasses import dataclass, field

import merge_request_handler


COMMIT = ("11", "msg1")


@dataclass
class MergeRequestStub():
    approved: bool = True
    has_conflicts: bool = False
    needs_rebase: bool = False
    no_commits: bool = False
    pipeline_status: str = "success"

    id: int = 7
    title: str = "Do Zorz at work"
    target_branch: str = "x/zorz_branch"
    merge_status: str = "can_be_merged"

    comments: list = field(default_factory=list, init=False)
    is_wip: bool = field(default=False, init=False)
    rebased: bool = field(default=False, init=False)
    merged: bool = field(default=False, init=False)

    def approvals_left(self):
        return 0 if self.approved else 1

    def last_commit_message(self):
        return COMMIT[1] if not self.no_commits else None

    def pipelines(self):
        if not self.pipeline_status:
            return []
        return [{"id": 7, "sha": COMMIT[0], "status": self.pipeline_status}]

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
        self.pipeline_status = "running"


@pytest.fixture
def mr_handler(monkeypatch):
    handler = merge_request_handler.MergeRequestHandler(None)

    def stub_get_commit_message(sha):
        return COMMIT[1]

    monkeypatch.setattr(handler, "_get_commit_message", stub_get_commit_message)
    return handler


testdata = [
    (
        # MR not approved: -> nothing changed
        {"approved": False},
        {"wip": False, "comments": 0, "rebased": False, "merged": False, "pipeline_status": "success"}),
    (
        # MR has conflicts -> wip, comment
        {"has_conflicts": True},
        {"wip": True, "comments": 1, "rebased": False, "merged": False, "pipeline_status": "success"}),
    (
        # MR don't have commits -> nothing changed
        {"no_commits": True},
        {"wip": False, "comments": 0, "rebased": False, "merged": False, "pipeline_status": "success"}),
    (
        # Pipeline in progress -> nothing changed
        {"pipeline_status": "running"},
        {"wip": False, "comments": 0, "rebased": False, "merged": False, "pipeline_status": "running"}),
    (
        # No pipelines, needs rebase -> pipeline started, comment
        {"needs_rebase": True, "pipeline_status": None},
        {"wip": False, "comments": 1, "rebased": False, "merged": False, "pipeline_status": "running"}),
    (
        # No pipelines, no conflicts -> pipeline started, comment
        {"pipeline_status": None},
        {"wip": False, "comments": 1, "rebased": False, "merged": False, "pipeline_status": "running"}),
    (
        # Pipeline successfull, needs rebase -> rebased, not merged
        {"needs_rebase": True, "pipeline_status": "success"},
        {"wip": False, "comments": 0, "rebased": True, "merged": False, "pipeline_status": "success"}),
    (
        # Pipeline successfull, no conflicts -> merged, comment
        {"pipeline_status": "success"},
        {"wip": False, "comments": 1, "rebased": False, "merged": True, "pipeline_status": "success"}),
    (
        # Pipeline failed -> wip, comment
        {"pipeline_status": "failed"},
        {"wip": True, "comments": 1, "rebased": False, "merged": False, "pipeline_status": "failed"})
]


@pytest.mark.parametrize("mr_state,expected_state", testdata)
def test_merge_request_handler(mr_handler, mr_state, expected_state):
    mr = MergeRequestStub(**mr_state)
    mr_handler.handle(mr)
    assert expected_state["wip"] == mr.is_wip
    assert expected_state["rebased"] == mr.rebased
    assert expected_state["merged"] == mr.merged
    assert expected_state["pipeline_status"] == mr.pipeline_status
    assert expected_state["comments"] == len(mr.comments)
