import pytest

import tests.merge_request_stub
import robocat.merge_request_handler


@pytest.fixture
def mr_handler(monkeypatch):
    handler = robocat.merge_request_handler.MergeRequestHandler(None)

    def stub_get_commit_message(sha):
        return tests.merge_request_stub.COMMITS[sha]

    monkeypatch.setattr(handler, "_get_commit_message", stub_get_commit_message)
    return handler


class TestMergeRequest:
    def test_rebase(self, mr_handler):
        mr = tests.merge_request_stub.MergeRequestStub(needs_rebase=True)
        mr_handler.handle(mr)

        assert not mr.is_wip
        assert mr.rebased
        assert not mr.merged
        assert 0 == len(mr.comments), f"Got comments: {mr.comments}"
        assert "success" == mr.pipelines_list[0][1]

    def test_merge(self, mr_handler):
        mr = tests.merge_request_stub.MergeRequestStub()
        mr_handler.handle(mr)

        assert not mr.is_wip
        assert not mr.rebased
        assert mr.merged
        assert 1 == len(mr.comments), f"Got comments: {mr.comments}"
        assert "success" == mr.pipelines_list[0][1]

    @pytest.mark.parametrize("mr_state", [
        # Pipeline started ignoring approve because there was no pipelines ran at all.
        {
            "approved": False,
            "pipelines_list": []
        },
        # Pipeline started without rebase
        {
            "needs_rebase": True,
            "pipelines_list": [(tests.merge_request_stub.DEFAULT_COMMIT["sha"], "skipped")]
        },
        # Pipeline started even if there are non-resolved discusions
        {
            "blocking_discussions_resolved": False,
            "pipelines_list": [(tests.merge_request_stub.DEFAULT_COMMIT["sha"], "skipped")]
        },
        # Pipeline started if fail was in previous commit (before rebase or amend)
        {
            "commits": {
                "11": "same_msg",
                "22": "same_msg"},
            "pipelines_list": [
                ("11", "skipped"),
                ("22", "failed")]
        }
    ])
    def test_run_pipeline(self, mr_handler, mr_state):
        mr = tests.merge_request_stub.MergeRequestStub(**mr_state)
        mr_handler.handle(mr)

        assert not mr.is_wip
        assert not mr.rebased
        assert not mr.merged
        assert 1 == len(mr.comments), f"Got comments: {mr.comments}"
        assert (mr.last_commit()[0], "running") == mr.pipelines_list[0]

    @pytest.mark.parametrize("mr_state", [
        # MR not approved
        {"approved": False},
        # MR not approved, pipeline not started
        {
            "approved": False,
            "pipelines_list": [(tests.merge_request_stub.DEFAULT_COMMIT["sha"], "skipped")]
        },
        # MR not approved, there was already ran pipeline at another commit
        {
            "approved": False,
            "commits": {
                "11": "same_msg",
                "22": "another_msg"},
            "pipelines_list": [
                ("11", "skipped"),
                ("22", "failed")]},
        # MR don't have commits
        {"commits": {}},
        # Pipeline in progress
        {"pipelines_list": [(tests.merge_request_stub.DEFAULT_COMMIT["sha"], "running")]}
    ])
    def test_nothing_changed(self, mr_handler, mr_state):
        mr = tests.merge_request_stub.MergeRequestStub(**mr_state)
        pipelines_before = mr.pipelines_list
        mr_handler.handle(mr)

        assert not mr.is_wip
        assert not mr.rebased
        assert not mr.merged
        assert 0 == len(mr.comments), f"Got comments: {mr.comments}"
        assert pipelines_before == mr.pipelines_list

    @pytest.mark.parametrize("mr_state", [
        # MR has conflicts, should return even if not approved
        {"has_conflicts": True, "approved": False},
        # Pipeline successfull, blocking discussions
        {"blocking_discussions_resolved": False},
        # Failed pipeline
        {
            "commits": {
                "11": "same_msg",
                "22": "same_msg"},
            "pipelines_list": [
                ("11", "failed"),
                ("22", "skipped")]
        }
    ])
    def test_return_to_development(self, mr_handler, mr_state):
        mr = tests.merge_request_stub.MergeRequestStub(**mr_state)
        pipelines_before = mr.pipelines_list
        mr_handler.handle(mr)

        assert mr.is_wip
        assert not mr.rebased
        assert not mr.merged
        assert 1 == len(mr.comments), f"Got comments: {mr.comments}"
        assert pipelines_before == mr.pipelines_list
