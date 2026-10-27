# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Offline contract coverage for the Bitbucket forge adapter (#298): no network, a scripted transport."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibey_gh.bitbucket_transport import BitbucketTransport
from vibey_gh.forge_bitbucket import BitbucketForge
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface


class ScriptedTransport:
    """A deterministic transport double that records the exact API paths requested."""

    executable = "fake-bitbucket"

    def __init__(self, *responses: tuple[object, str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, ...]] = []

    def survey(self, args, *, cwd=None, stdin=None):
        del cwd, stdin
        self.calls.append(tuple(args))
        return self.responses.pop(0) if self.responses else ([], "")


def _forge(transport: ScriptedTransport) -> BitbucketForge:
    return BitbucketForge(root=Path("/repo"), repository="ws/repo", transport=transport)


PULL = {
    "id": 7,
    "title": "Title",
    "description": "Body",
    "state": "OPEN",
    "source": {"branch": {"name": "topic"}, "commit": {"hash": "abc"}},
    "destination": {"branch": {"name": "develop"}},
}


def test_the_adapter_satisfies_the_seam_and_defaults_to_the_bitbucket_transport():
    forge = BitbucketForge(root=Path("/repo"))
    assert isinstance(forge, ForgeAdapterInterface)
    assert isinstance(forge.transport, BitbucketTransport)
    assert forge.for_repository("ws/repo").repository == "ws/repo"


def test_artifact_listing_asks_for_every_pull_request_state_and_honours_the_limit():
    transport = ScriptedTransport(([{"id": 1}, "ignored", {"id": 2}, {"id": 3}], ""))
    items, problem = _forge(transport).list_artifacts(
        "change-request", since="2026-01-01T00:00:00Z", page=2, limit=2
    )
    assert items == [{"id": 1}, {"id": 2}] and not problem
    path = transport.calls[0][0]
    assert path.startswith("repositories/ws/repo/pullrequests?state=OPEN&state=MERGED")
    assert "page=2&pagelen=2" in path
    assert "q=updated_on%3E%222026-01-01T00%3A00%3A00Z%22" in path

    issues = ScriptedTransport(([{"id": 1}], ""))
    _forge(issues).list_artifacts("issue")
    assert issues.calls[0][0] == "repositories/ws/repo/issues?page=1&pagelen=100"

    assert _forge(ScriptedTransport()).list_artifacts("unknown")[1].startswith("Bitbucket adapter")
    assert _forge(ScriptedTransport(([], "down"))).list_artifacts("issue") == ([], "down")
    assert _forge(ScriptedTransport(({}, ""))).list_artifacts("issue") == (
        [],
        "Expected list of artifacts",
    )


def test_open_change_request_heads_reads_source_branches():
    pulls = [PULL, {"source": {"branch": {}}}, {"source": {"branch": "flat"}}, "not-a-pull"]
    transport = ScriptedTransport((pulls, ""))
    assert _forge(transport).open_change_request_heads(limit=5) == (frozenset({"topic"}), "")
    assert transport.calls[0][0] == "repositories/ws/repo/pullrequests?state=OPEN&pagelen=5"
    assert _forge(ScriptedTransport(([], "down"))).open_change_request_heads(limit=1) == (
        frozenset(),
        "down",
    )
    assert _forge(ScriptedTransport(({}, ""))).open_change_request_heads(limit=1)[1]


def test_reads_every_neutral_verb():
    change, problem = _forge(ScriptedTransport((PULL, ""))).get_change_request(7)
    assert not problem and change is not None
    assert (change.number, change.head_ref, change.head_sha, change.base_ref) == (
        7,
        "topic",
        "abc",
        "develop",
    )
    assert (change.title, change.body, change.state) == ("Title", "Body", "OPEN")
    assert _forge(ScriptedTransport(([], ""))).get_change_request(7)[1] == (
        "Expected object for PR 7"
    )
    assert _forge(ScriptedTransport(([], "down"))).get_change_request(7) == (None, "down")

    issue = {"id": 8, "title": "Bug", "content": {"raw": "Text"}, "state": "new"}
    got = _forge(ScriptedTransport((issue, ""))).get_issue(8)[0]
    assert got is not None and (got.number, got.body, got.state) == (8, "Text", "new")
    assert _forge(ScriptedTransport(([], ""))).get_issue(8)[1] == "Expected object for issue 8"
    assert _forge(ScriptedTransport(([], "down"))).get_issue(8) == (None, "down")

    comment = {"id": 3, "user": {"nickname": "ada"}, "content": {"raw": "hi"}}
    thread = _forge(ScriptedTransport(([comment, "ignored"], ""))).get_issue_thread(8)[0]
    assert [(c.id, c.author, c.body) for c in thread] == [("3", "ada", "hi")]
    fallback = ScriptedTransport(([], "no issue"), ([comment], ""))
    assert len(_forge(fallback).get_issue_thread(8)[0]) == 1
    assert fallback.calls[1][0] == "repositories/ws/repo/pullrequests/8/comments"
    assert _forge(ScriptedTransport(([], "first"), ([], "second"))).get_issue_thread(8) == (
        (),
        "second",
    )
    assert _forge(ScriptedTransport(({}, ""))).get_issue_thread(8)[1] == (
        "Comments field is not a list"
    )


def test_reviews_come_from_reviewer_participants_with_a_verdict():
    participants = [
        {"role": "REVIEWER", "approved": True, "user": {"account_id": "a1", "nickname": "bo"}},
        {"role": "REVIEWER", "state": "changes_requested", "user": {"uuid": "{u2}"}},
        {"role": "REVIEWER", "state": "approved", "user": {"display_name": "Cy"}},
        {"role": "REVIEWER", "approved": False, "user": {"nickname": "silent"}},
        {"role": "PARTICIPANT", "approved": True, "user": {"nickname": "author"}},
        "ignored",
    ]
    reviews, problem = _forge(ScriptedTransport(({"participants": participants}, ""))).get_reviews(
        7
    )
    assert not problem
    assert [(r.id, r.author, r.verdict) for r in reviews] == [
        ("a1", "bo", "APPROVED"),
        ("{u2}", "", "CHANGES_REQUESTED"),
        ("", "Cy", "APPROVED"),
    ]
    assert _forge(ScriptedTransport(({}, ""))).get_reviews(7) == ((), "")
    assert _forge(ScriptedTransport(({"participants": {}}, ""))).get_reviews(7)[1] == (
        "Participants field is not a list"
    )
    assert _forge(ScriptedTransport(([], ""))).get_reviews(7)[1] == "Expected object for PR 7"
    assert _forge(ScriptedTransport(([], "down"))).get_reviews(7) == ((), "down")


def test_check_results_map_states_and_leave_unfinished_checks_unfinished():
    statuses = [
        {"name": "CI", "state": "SUCCESSFUL"},
        {"key": "lint", "state": "FAILED"},
        {"name": "build", "state": "STOPPED"},
        {"name": "slow", "state": "INPROGRESS"},
        "ignored",
    ]
    transport = ScriptedTransport((statuses, ""))
    results, problem = _forge(transport).get_check_results("abc")
    assert not problem
    assert [(r["name"], r["conclusion"]) for r in results] == [
        ("CI", "success"),
        ("lint", "failure"),
        ("build", "cancelled"),
        ("slow", ""),
    ]
    assert transport.calls[0][0] == "repositories/ws/repo/commit/abc/statuses"
    assert _forge(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")
    assert _forge(ScriptedTransport(({}, ""))).get_check_results("abc")[1] == (
        "Check results are not a list"
    )


def test_comments_are_posted_to_the_pull_request_then_the_issue():
    reply = {"id": 9, "user": {"nickname": "me"}, "content": {"raw": "body"}}
    transport = ScriptedTransport((reply, ""))
    comment = _forge(transport).create_comment(7, "body")[0]
    assert comment is not None and (comment.id, comment.author) == ("9", "me")
    assert transport.calls[0] == (
        "repositories/ws/repo/pullrequests/7/comments",
        "POST",
        json.dumps({"content": {"raw": "body"}}),
    )
    fallback = ScriptedTransport(([], "not a pull request"), ({}, ""))
    assert _forge(fallback).create_comment(7, "body")[0].body == "body"
    assert fallback.calls[1][0] == "repositories/ws/repo/issues/7/comments"
    assert _forge(ScriptedTransport(([], "first"), ([], "second"))).create_comment(7, "b") == (
        None,
        "second",
    )


def test_updating_and_merging_a_change_request():
    edit = ScriptedTransport(({}, ""), (PULL, ""))
    updated = _forge(edit).update_change_request(7, "New", "Text")[0]
    assert updated is not None and updated.title == "Title"
    assert edit.calls[0] == (
        "repositories/ws/repo/pullrequests/7",
        "PUT",
        json.dumps({"title": "New", "description": "Text"}),
    )
    assert _forge(ScriptedTransport(([], "denied"))).update_change_request(7) == (None, "denied")

    for method, strategy in (
        ("squash", "squash"),
        ("merge", "merge_commit"),
        ("rebase", "fast_forward"),
    ):
        merge = ScriptedTransport(({}, ""))
        assert _forge(merge).merge_change_request(7, method) == (True, "")
        assert merge.calls[0] == (
            "repositories/ws/repo/pullrequests/7/merge",
            "POST",
            json.dumps({"merge_strategy": strategy}),
        )
    assert _forge(ScriptedTransport(([], "denied"))).merge_change_request(7) == (False, "denied")
    unknown, problem = _forge(ScriptedTransport()).merge_change_request(7, "octopus")
    assert not unknown and "no merge method 'octopus'" in problem


def test_branch_protection_is_a_pair_of_rewrite_restrictions():
    protect = ScriptedTransport(({}, ""), ({}, ""))
    assert _forge(protect).set_protected_ref("main", True) == (True, "")
    assert [json.loads(call[2])["kind"] for call in protect.calls] == ["force", "delete"]
    assert json.loads(protect.calls[0][2])["pattern"] == "main"
    assert _forge(ScriptedTransport(([], "denied"))).set_protected_ref("main", True) == (
        False,
        "denied",
    )

    rows = [
        {"id": 1, "kind": "force", "pattern": "main"},
        {"id": 2, "kind": "delete", "pattern": "main"},
        {"id": 3, "kind": "force", "pattern": "other"},
        {"id": 4, "kind": "require_approvals_to_merge", "pattern": "main"},
        "ignored",
    ]
    unprotect = ScriptedTransport((rows, ""), ({}, ""), ({}, ""))
    assert _forge(unprotect).set_protected_ref("main", False) == (True, "")
    assert [call[:2] for call in unprotect.calls[1:]] == [
        ("repositories/ws/repo/branch-restrictions/1", "DELETE"),
        ("repositories/ws/repo/branch-restrictions/2", "DELETE"),
    ]
    assert _forge(ScriptedTransport(([], "down"))).set_protected_ref("main", False) == (
        False,
        "down",
    )
    assert _forge(ScriptedTransport(({}, ""))).set_protected_ref("main", False)[1] == (
        "Expected list of branch restrictions"
    )
    failing = ScriptedTransport(([{"id": 1, "kind": "force", "pattern": "main"}], ""), ([], "no"))
    assert _forge(failing).set_protected_ref("main", False) == (False, "no")

    listing = [*rows, {"kind": "push", "pattern": ""}]
    assert _forge(ScriptedTransport((listing, ""))).get_protected_refs() == (
        frozenset({"main", "other"}),
        "",
    )
    assert _forge(ScriptedTransport(([], "down"))).get_protected_refs() == (frozenset(), "down")
    assert _forge(ScriptedTransport(({}, ""))).get_protected_refs()[1] == (
        "Expected list of branch restrictions"
    )


@pytest.mark.parametrize(
    ("call", "verb"),
    [
        (lambda f: f.releases(limit=3)[1], "releases"),
        (lambda f: f.create_release("v1", "One", "Body")[1], "creating a release"),
        (lambda f: f.list_artifacts("release")[1], "release listing"),
        (lambda f: f.list_artifacts("label")[1], "label listing"),
        (lambda f: f.merge_change_request(7, admin=True)[1], "an administrator merge"),
    ],
)
def test_every_verb_bitbucket_cannot_express_names_itself_and_never_calls_out(call, verb):
    transport = ScriptedTransport()
    problem = call(_forge(transport))
    assert problem.startswith(f"bitbucket does not support {verb}: ")
    assert transport.calls == []


def test_unsupported_verbs_return_no_value():
    forge = _forge(ScriptedTransport())
    assert forge.releases(limit=3)[0] == ()
    assert forge.create_release("v1", "One", "Body")[0] is None
    assert forge.list_artifacts("label")[0] == []
    assert forge.merge_change_request(7, admin=True)[0] is False
