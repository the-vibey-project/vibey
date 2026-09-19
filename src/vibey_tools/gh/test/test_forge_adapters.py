# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Offline contract coverage for the forge-neutral adapter and transport seams."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path

import pytest

from vibey_gh.forge import ForgeReview
from vibey_gh.forge_adapter_reader import ForgeAdapterReader, moment, stamp
from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_github import GitHubForge
from vibey_gh.forge_gitlab import GitLabForge
from vibey_gh.forgejo_transport import ForgejoTransport
from vibey_gh.gitlab_transport import GitLabTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_snapshot_interface import ForgeReaderInterface
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface


class ScriptedTransport:
    """A deterministic transport double that records the exact API paths requested."""

    executable = "fake-forge"

    def __init__(self, *responses: tuple[object, str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, ...]] = []

    def survey(self, args, *, cwd=None, stdin=None):
        del cwd, stdin
        self.calls.append(tuple(args))
        return self.responses.pop(0) if self.responses else ([], "")


def _github(transport: ScriptedTransport) -> GitHubForge:
    return GitHubForge(root=Path("/repo"), transport=transport)


def _gitlab(transport: ScriptedTransport) -> GitLabForge:
    return GitLabForge(root=Path("/repo"), transport=transport)


def _forgejo(transport: ScriptedTransport) -> ForgejoForge:
    return ForgejoForge(root=Path("/repo"), transport=transport)


def test_github_artifact_listing_and_list_verbs_cover_the_shape_contract():
    transport = ScriptedTransport(([{"id": 1}, "ignored", {"id": 2}], ""))
    items, problem = _github(transport).list_artifacts("issue", since="2026-01-01", page=2, limit=3)
    assert items == [{"id": 1}, {"id": 2}] and not problem
    assert "page=2" in transport.calls[0][1]
    assert "per_page=3" in transport.calls[0][1]
    assert "since=2026-01-01" in transport.calls[0][1]

    assert _github(ScriptedTransport()).list_artifacts("unknown")[1] == (
        "GitHub adapter does not support artifact class 'unknown'"
    )
    assert _github(ScriptedTransport(([], "down"))).list_artifacts("issue") == ([], "down")
    assert _github(ScriptedTransport(({}, ""))).list_artifacts("issue") == (
        [],
        "Expected list of artifacts",
    )

    heads = _github(
        ScriptedTransport(([{"headRefName": "topic"}, {"headRefName": None}, "not-a-pull"], ""))
    )
    assert heads.open_change_request_heads(limit=4) == (frozenset({"topic"}), "")

    releases = _github(
        ScriptedTransport(([{"tagName": "v1", "name": "One", "isDraft": True}, "ignored"], ""))
    )
    assert releases.releases(limit=4)[0][0].draft
    assert _github(ScriptedTransport(({}, ""))).open_change_request_heads(limit=1)[1]
    assert _github(ScriptedTransport(([], "failed"))).releases(limit=1) == ((), "failed")


def test_github_reads_and_writes_every_neutral_verb():
    change = {
        "number": 7,
        "headRefName": "topic",
        "headRefOid": "abc",
        "baseRefName": "develop",
        "title": "Title",
        "body": "Body",
        "state": "OPEN",
    }
    assert _github(ScriptedTransport((change, ""))).get_change_request(7)[0].head_sha == "abc"
    assert (
        _github(ScriptedTransport(([], ""))).get_change_request(7)[1] == "Expected object for PR 7"
    )
    assert _github(ScriptedTransport(([], "down"))).get_change_request(7) == (None, "down")

    issue = {"number": 8, "title": "Bug", "body": "Body", "state": "OPEN"}
    assert _github(ScriptedTransport((issue, ""))).get_issue(8)[0].title == "Bug"
    assert _github(ScriptedTransport(([], "down"))).get_issue(8) == (None, "down")
    assert _github(ScriptedTransport(([], ""))).get_issue(8)[1] == "Expected object for issue 8"

    comments = {"comments": [{"id": 1, "author": "ada", "body": "hi"}, "ignored"]}
    assert len(_github(ScriptedTransport((comments, ""))).get_issue_thread(8)[0]) == 1
    assert _github(ScriptedTransport(([], "down"))).get_issue_thread(8) == ((), "down")
    assert (
        _github(ScriptedTransport(([], ""))).get_issue_thread(8)[1] == "Expected object for issue 8"
    )
    assert _github(ScriptedTransport(({"comments": {}}, ""))).get_issue_thread(8)[1] == (
        "Comments field is not a list"
    )

    review = {"id": 2, "user": {"login": "bo"}, "state": "APPROVED", "body": "yes"}
    assert _github(ScriptedTransport(([review, "ignored"], ""))).get_reviews(7)[0][0].author == "bo"
    assert _github(ScriptedTransport(({}, ""))).get_reviews(7)[1] == "Expected list of reviews"
    assert _github(ScriptedTransport(([], "down"))).get_reviews(7) == ((), "down")

    checks = {"check_runs": [{"name": "CI", "conclusion": "success"}, "ignored"]}
    assert _github(ScriptedTransport((checks, ""))).get_check_results("abc")[0][0]["name"] == "CI"
    assert _github(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")
    assert _github(ScriptedTransport(([], ""))).get_check_results("abc")[1] == (
        "Expected object for check-runs"
    )
    assert _github(ScriptedTransport(({"check_runs": {}}, ""))).get_check_results("abc")[1] == (
        "check_runs field is not a list"
    )

    assert _github(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
    assert _github(ScriptedTransport(([], "down"))).create_comment(7, "body") == (None, "down")

    update_transport = ScriptedTransport(({}, ""), (change, ""))
    updated, problem = _github(update_transport).update_change_request(7, "New", "Text")
    assert updated is not None and not problem
    assert update_transport.calls[0] == ("pr", "edit", "7", "-t", "New", "-b", "Text")
    no_fields = ScriptedTransport(({}, ""), (change, ""))
    assert _github(no_fields).update_change_request(7) == (updated, "")
    assert _github(ScriptedTransport(([], "denied"))).update_change_request(7) == (None, "denied")

    assert _github(ScriptedTransport(({}, ""))).merge_change_request(7, admin=True) == (True, "")
    assert _github(ScriptedTransport(([], "denied"))).merge_change_request(7) == (False, "denied")
    assert (
        _github(ScriptedTransport(({}, "")))
        .create_release("v1", "One", "body", draft=True)[0]
        .draft
    )
    assert _github(ScriptedTransport(([], "denied"))).create_release("v1", "One", "body") == (
        None,
        "denied",
    )
    assert _github(ScriptedTransport(({}, ""))).set_protected_ref("main", True) == (True, "")
    assert _github(ScriptedTransport(({}, ""))).set_protected_ref("main", False) == (True, "")
    assert _github(ScriptedTransport(([], "denied"))).set_protected_ref("main", True) == (
        False,
        "denied",
    )
    protected = _github(
        ScriptedTransport(([{"name": "main", "protected": True}, {"name": "dev"}], ""))
    )
    assert protected.get_protected_refs() == (frozenset({"main"}), "")
    assert _github(ScriptedTransport(([], "down"))).get_protected_refs() == (frozenset(), "down")
    assert _github(ScriptedTransport(({}, ""))).get_protected_refs() == (
        frozenset(),
        "Expected list of branches",
    )


def test_gitlab_adapter_covers_list_and_mutation_paths():
    assert isinstance(_gitlab(ScriptedTransport()), ForgeAdapterInterface)
    adapter = _gitlab(ScriptedTransport(([{"id": 1}, "ignored"], "")))
    assert adapter.list_artifacts("issue", since="yesterday", page=2, limit=4)[0] == [{"id": 1}]
    assert _gitlab(ScriptedTransport()).list_artifacts("unknown")[1].startswith("GitLab adapter")
    assert (
        _gitlab(ScriptedTransport(({}, ""))).list_artifacts("issue")[1]
        == "Expected list of artifacts"
    )
    assert _gitlab(ScriptedTransport(([], "down"))).list_artifacts("issue") == ([], "down")

    pulls = _gitlab(ScriptedTransport(([{"source_branch": "topic"}, "ignored"], "")))
    assert pulls.open_change_request_heads(limit=3) == (frozenset({"topic"}), "")
    assert _gitlab(ScriptedTransport(([], "down"))).open_change_request_heads(limit=3) == (
        frozenset(),
        "down",
    )
    releases = _gitlab(ScriptedTransport(([{"tag_name": "v1", "name": "One"}, "ignored"], "")))
    assert releases.releases(limit=3)[0][0].tag == "v1"
    assert _gitlab(ScriptedTransport(([], "down"))).releases(limit=3) == ((), "down")

    mr = {
        "iid": 7,
        "source_branch": "topic",
        "sha": "abc",
        "target_branch": "main",
        "title": "MR",
        "description": "Body",
        "state": "opened",
    }
    assert _gitlab(ScriptedTransport((mr, ""))).get_change_request(7)[0].number == 7
    assert (
        _gitlab(ScriptedTransport(([], ""))).get_change_request(7)[1] == "Expected object for MR 7"
    )
    assert _gitlab(ScriptedTransport(([], "down"))).get_change_request(7) == (None, "down")
    issue = {"iid": 8, "title": "Bug", "description": "Body", "state": "opened"}
    assert _gitlab(ScriptedTransport((issue, ""))).get_issue(8)[0].number == 8
    assert _gitlab(ScriptedTransport(([], ""))).get_issue(8)[1] == "Expected object for issue 8"
    assert _gitlab(ScriptedTransport(([], "down"))).get_issue(8) == (None, "down")

    notes = [{"id": 1, "author": {"username": "ada"}, "body": "hi"}]
    assert _gitlab(ScriptedTransport((notes, ""))).get_issue_thread(8)[0][0].author == "ada"
    fallback = ScriptedTransport(([], "not issue"), (notes, ""))
    assert _gitlab(fallback).get_issue_thread(8)[0][0].body == "hi"
    assert _gitlab(ScriptedTransport(([], "first"), ([], "second"))).get_issue_thread(8) == (
        (),
        "second",
    )
    assert (
        _gitlab(ScriptedTransport(({}, ""))).get_issue_thread(8)[1]
        == "Comments field is not a list"
    )
    assert _gitlab(ScriptedTransport(([], "down"))).get_reviews(7) == ((), "down")
    assert (
        _gitlab(ScriptedTransport(([], ""))).get_reviews(7)[1]
        == "Approvals response is not an object"
    )
    assert (
        _gitlab(ScriptedTransport(({"approved": True}, ""))).get_reviews(7)[0][0].verdict
        == "APPROVED"
    )
    assert _gitlab(ScriptedTransport(({"approved": False}, ""))).get_reviews(7) == ((), "")
    statuses = [{"name": "CI", "status": "success"}]
    assert (
        _gitlab(ScriptedTransport((statuses, ""))).get_check_results("abc")[0][0]["conclusion"]
        == "success"
    )
    assert (
        _gitlab(ScriptedTransport(({}, ""))).get_check_results("abc")[1]
        == "Check results are not a list"
    )
    assert _gitlab(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")

    assert _gitlab(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
    assert (
        _gitlab(ScriptedTransport(([], "first"), ({}, ""))).create_comment(7, "body")[0].body
        == "body"
    )
    assert _gitlab(ScriptedTransport(([], "first"), ([], "second"))).create_comment(7, "body") == (
        None,
        "second",
    )
    edit = ScriptedTransport(({}, ""), (mr, ""))
    assert _gitlab(edit).update_change_request(7, "Title", "Body")[0].title == "MR"
    assert _gitlab(ScriptedTransport(([], "down"))).update_change_request(7) == (None, "down")
    assert _gitlab(ScriptedTransport(({}, ""))).merge_change_request(7) == (True, "")
    assert _gitlab(ScriptedTransport(([], "down"))).merge_change_request(7) == (False, "down")
    assert _gitlab(ScriptedTransport(({}, ""))).create_release("v1", "One", "Body")[0].tag == "v1"
    assert _gitlab(ScriptedTransport(([], "down"))).create_release("v1", "One", "Body") == (
        None,
        "down",
    )
    assert _gitlab(ScriptedTransport(({}, ""))).set_protected_ref("main", True) == (True, "")
    assert _gitlab(ScriptedTransport(({}, ""))).set_protected_ref("main", False) == (True, "")
    assert _gitlab(ScriptedTransport(([], "down"))).set_protected_ref("main", True) == (
        False,
        "down",
    )
    assert _gitlab(ScriptedTransport(([{"name": "main"}, "ignored"], ""))).get_protected_refs() == (
        frozenset({"main"}),
        "",
    )
    assert (
        _gitlab(ScriptedTransport(({}, ""))).get_protected_refs()[1]
        == "Expected list of protected branches"
    )
    assert _gitlab(ScriptedTransport(([], "down"))).get_protected_refs() == (frozenset(), "down")


def test_forgejo_adapter_covers_list_and_mutation_paths():
    assert isinstance(_forgejo(ScriptedTransport()), ForgeAdapterInterface)
    assert _forgejo(ScriptedTransport(([{"id": 1}, "ignored"], ""))).list_artifacts(
        "issue", since="yesterday"
    )[0] == [{"id": 1}]
    assert _forgejo(ScriptedTransport()).list_artifacts("unknown")[1].startswith("Forgejo adapter")
    assert (
        _forgejo(ScriptedTransport(({}, ""))).list_artifacts("issue")[1]
        == "Expected list of artifacts"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).list_artifacts("issue") == ([], "down")
    assert _forgejo(
        ScriptedTransport(([{"head": {"branch": "topic"}}, "ignored"], ""))
    ).open_change_request_heads(limit=3) == (
        frozenset({"topic"}),
        "",
    )
    assert _forgejo(ScriptedTransport(([], "down"))).open_change_request_heads(limit=3) == (
        frozenset(),
        "down",
    )
    assert (
        _forgejo(ScriptedTransport(([{"tag_name": "v1", "name": "One"}, "ignored"], "")))
        .releases(limit=3)[0][0]
        .tag
        == "v1"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).releases(limit=3) == ((), "down")

    pr = {
        "id": 7,
        "head": {"branch": "topic", "sha": "abc"},
        "base": {"ref": "main"},
        "title": "PR",
        "body": "Body",
        "state": "open",
    }
    assert _forgejo(ScriptedTransport((pr, ""))).get_change_request(7)[0].head_ref == "topic"
    assert (
        _forgejo(ScriptedTransport(([], ""))).get_change_request(7)[1] == "Expected object for PR 7"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).get_change_request(7) == (None, "down")
    issue = {"id": 8, "title": "Bug", "body": "Body", "state": "open"}
    assert _forgejo(ScriptedTransport((issue, ""))).get_issue(8)[0].number == 8
    assert _forgejo(ScriptedTransport(([], ""))).get_issue(8)[1] == "Expected object for issue 8"
    assert _forgejo(ScriptedTransport(([], "down"))).get_issue(8) == (None, "down")

    comments = [{"id": 1, "user": {"username": "ada"}, "body": "hi"}]
    assert _forgejo(ScriptedTransport((comments, ""))).get_issue_thread(8)[0][0].author == "ada"
    fallback = ScriptedTransport(([], "not issue"), (comments, ""))
    assert _forgejo(fallback).get_issue_thread(8)[0][0].body == "hi"
    assert _forgejo(ScriptedTransport(([], "first"), ([], "second"))).get_issue_thread(8) == (
        (),
        "second",
    )
    assert (
        _forgejo(ScriptedTransport(({}, ""))).get_issue_thread(8)[1]
        == "Comments field is not a list"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).get_reviews(7) == ((), "down")
    assert _forgejo(ScriptedTransport(({}, ""))).get_reviews(7) == ((), "")
    statuses = [{"context": "CI", "state": "success"}]
    assert (
        _forgejo(ScriptedTransport((statuses, ""))).get_check_results("abc")[0][0]["name"] == "CI"
    )
    assert (
        _forgejo(ScriptedTransport(({}, ""))).get_check_results("abc")[1]
        == "Check results are not a list"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")

    assert _forgejo(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
    assert (
        _forgejo(ScriptedTransport(([], "first"), ({}, ""))).create_comment(7, "body")[0].body
        == "body"
    )
    assert _forgejo(ScriptedTransport(([], "first"), ([], "second"))).create_comment(7, "body") == (
        None,
        "second",
    )
    edit = ScriptedTransport(({}, ""), (pr, ""))
    assert _forgejo(edit).update_change_request(7, "Title", "Body")[0].title == "PR"
    assert _forgejo(ScriptedTransport(([], "down"))).update_change_request(7) == (None, "down")
    assert _forgejo(ScriptedTransport(({}, ""))).merge_change_request(7) == (True, "")
    assert _forgejo(ScriptedTransport(([], "down"))).merge_change_request(7) == (False, "down")
    assert _forgejo(ScriptedTransport(({}, ""))).create_release("v1", "One", "Body")[0].tag == "v1"
    assert _forgejo(ScriptedTransport(([], "down"))).create_release("v1", "One", "Body") == (
        None,
        "down",
    )
    assert _forgejo(ScriptedTransport(({}, ""))).set_protected_ref("main", True) == (True, "")
    assert _forgejo(ScriptedTransport(({}, ""))).set_protected_ref("main", False) == (True, "")
    assert _forgejo(ScriptedTransport(([], "down"))).set_protected_ref("main", True) == (
        False,
        "down",
    )
    assert _forgejo(
        ScriptedTransport(([{"branch": "main"}, "ignored"], ""))
    ).get_protected_refs() == (
        frozenset({"main"}),
        "",
    )
    assert (
        _forgejo(ScriptedTransport(({}, ""))).get_protected_refs()[1]
        == "Expected list of protected branches"
    )
    assert _forgejo(ScriptedTransport(([], "down"))).get_protected_refs() == (frozenset(), "down")


def test_forge_adapter_reader_pages_reviews_and_rejects_lossy_shapes():
    class Adapter:
        def __init__(self, listings, reviews=()) -> None:
            self.listings = listings
            self.reviews = reviews
            self.calls = []

        def list_artifacts(self, forge_class, since=None, page=1, limit=100):
            self.calls.append((forge_class, since, page, limit))
            value = self.listings.get((forge_class, page), ([], ""))
            return value

        def get_reviews(self, number):
            return self.reviews

    adapter = Adapter({("issue", 1): ([{"id": 1}], "")})
    reader = ForgeAdapterReader("github", "o/r", adapter, per_page=2)
    assert isinstance(reader, ForgeReaderInterface)
    assert reader.read("issue", "cursor").observations == (("1", {"id": 1}),)
    assert adapter.calls == [("issue", "cursor", 1, 2)]

    paged = Adapter({("label", 1): ([{"id": 1, "name": "one"}], ""), ("label", 2): ([], "")})
    assert ForgeAdapterReader("github", "o/r", paged, per_page=1).read("label", None).problem == ""
    assert (
        ForgeAdapterReader("github", "o/r", Adapter({("issue", 1): ([], "down")}))
        .read("issue", None)
        .problem
        == "down"
    )
    assert (
        ForgeAdapterReader("github", "o/r", Adapter({("issue", 1): ([{}], "")}))
        .read("issue", None)
        .problem
    )

    review_adapter = Adapter(
        {("change-request", 1): ([{"id": 7, "number": 7}], "")},
        ((ForgeReview("r1", "ada", "APPROVED", "yes"),), ""),
    )
    review = ForgeAdapterReader("github", "o/r", review_adapter, per_page=2).read("review", None)
    assert review.observations == (
        ("r1", {"id": "r1", "author": "ada", "verdict": "APPROVED", "body": "yes"}),
    )

    bad_number = Adapter({("change-request", 1): ([{"id": 7, "number": "7"}], "")})
    assert ForgeAdapterReader("github", "o/r", bad_number).read("review", None).observations == ()
    review_error = Adapter({("change-request", 1): ([{"id": 7, "number": 7}], "")}, ((), "down"))
    assert ForgeAdapterReader("github", "o/r", review_error).read("review", None).problem == "down"
    listing_error = Adapter({("change-request", 1): ([], "down")})
    assert (
        "could not be listed"
        in ForgeAdapterReader("github", "o/r", listing_error).read("review", None).problem
    )
    iid = Adapter({("change-request", 1): ([{"iid": 7}], "")})
    iid_read = ForgeAdapterReader("gitlab", "o/r", iid).read("change-request", None)
    assert iid_read.observations == (("7", {"iid": 7}),)
    stamped = Adapter({("issue", 1): ([{"id": 1, "updated_at": "2026-01-02T00:00:00Z"}], "")})
    assert (
        ForgeAdapterReader("github", "o/r", stamped).read("issue", None).high_water
        == "2026-01-02T00:00:00Z"
    )
    assert (
        ForgeAdapterReader._high_water(
            [{"id": 1, "updated_at": "not-a-time", "created_at": "2026-01-01T00:00:00Z"}]
        )
        == "2026-01-01T00:00:00Z"
    )
    assert _github(ScriptedTransport()).for_repository("o/r").repository == "o/r"
    assert _gitlab(ScriptedTransport()).for_repository("o/r").repository == "o/r"
    assert _forgejo(ScriptedTransport()).for_repository("o/r").repository == "o/r"
    bound_reader = ForgeAdapterReader("github", "o/r", _github(ScriptedTransport()))
    assert bound_reader.adapter.repository == "o/r"
    with pytest.raises(ValueError, match="unknown artifact class"):
        ForgeAdapterReader("github", "o/r", Adapter({})).read("unknown", None)


@pytest.mark.parametrize("value", ["2026-01-01T00:00:00", "2026-01-01T00:00:00+00:00"])
def test_reader_moments_are_utc_and_stable(value):
    assert stamp(moment(value)) == "2026-01-01T00:00:00Z"


class _HttpResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload.encode()


@pytest.mark.parametrize(
    "transport_type, header",
    [(GitLabTransport, "PRIVATE-TOKEN"), (ForgejoTransport, "Authorization")],
)
def test_http_transports_cover_success_and_failures(monkeypatch, transport_type, header):
    transport = transport_type(host="forge.example", token="secret")
    assert isinstance(transport, ForgeTransportInterface)
    assert transport.executable.startswith("http")
    assert transport.run([])[0] is False
    assert transport.survey([]) == ([], "No API path provided")
    seen = {}

    def success(request):
        seen.update({key.lower(): value for key, value in request.header_items()})
        return _HttpResponse(json.dumps([{"id": 1}]))

    monkeypatch.setattr("urllib.request.urlopen", success)
    assert transport.survey(["projects/1/issues"])[0] == [{"id": 1}]
    assert seen[header.lower()] in {"secret", "token secret"}
    assert transport.survey(["projects/1/issues", "POST", '{"body":"x"}'])[0] == [{"id": 1}]
    assert seen["content-type"] == "application/json"

    monkeypatch.setattr("urllib.request.urlopen", lambda request: _HttpResponse('{"ok": true}'))
    assert transport.survey(["one"])[0] == {"ok": True}
    monkeypatch.setattr("urllib.request.urlopen", lambda request: _HttpResponse('"scalar"'))
    assert "neither a list nor an object" in transport.survey(["one"])[1]
    error = urllib.error.HTTPError("https://forge.example", 401, "Unauthorized", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", lambda request: (_ for _ in ()).throw(error))
    assert "API error 401" in transport.survey(["one"])[1]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request: (_ for _ in ()).throw(OSError("offline"))
    )
    assert "transport failure: offline" in transport.survey(["one"])[1]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request: (_ for _ in ()).throw(TimeoutError("late"))
    )
    assert "transport failure: late" in transport.survey(["one"])[1]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request: (_ for _ in ()).throw(ValueError("bad json"))
    )
    assert "transport failure: bad json" in transport.survey(["one"])[1]
