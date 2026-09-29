# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One tracking issue per condition, over an in-memory forge that answers like the REST API.

`FakeForge` is shared with test_branch_health.py: it keeps issues and comments, answers
the calls `TrackingIssue` makes, and records every argv so a test can assert what was
never sent.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from typing import Any

import pytest

from vibey_gh import cli
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.tracking_issue_interface import TrackingIssueInterface
from vibey_gh.tracking_issue import TrackingIssue

REPO = "o/r"


class FakeForge:
    """Just enough of the forge's REST API for the tracking issue and branch health."""

    executable = "gh"

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.comments: dict[int, list[dict[str, Any]]] = {}
        self.calls: list[tuple[str, ...]] = []
        self.extra: dict[str, Any] = {}
        self.fail: str = ""

    # --- the transport surface ------------------------------------------------------

    def run(self, args: Sequence[str], *, cwd=None, stdin=None) -> subprocess.CompletedProcess:
        self.calls.append(tuple(args))
        if self.fail and self.fail in " ".join(args):
            return subprocess.CompletedProcess(list(args), 1, "", "HTTP 502")
        path = next(a for a in args if a.startswith("repos/"))
        if path in self.extra:
            return subprocess.CompletedProcess(list(args), 0, self.extra[path], "")
        if path.startswith(f"repos/{REPO}/issues?"):
            listed = [dict(issue) for issue in self.issues.values() if issue["state"] == "open"]
            # Two pages, the old concatenated shape, to prove both decode.
            half = len(listed) // 2
            out = json.dumps(listed[:half]) + json.dumps(listed[half:])
            return subprocess.CompletedProcess(list(args), 0, out, "")
        number = int(path.split("/")[4].split("?")[0])
        out = json.dumps(self.comments.get(number, []))
        return subprocess.CompletedProcess(list(args), 0, out, "")

    def json(self, args: Sequence[str], *, cwd=None, stdin=None) -> Any:
        self.calls.append(tuple(args))
        path = args[1]
        if self.fail and self.fail in " ".join(args):
            raise RuntimeError(f"gh {' '.join(args)}: HTTP 502")
        if path in self.extra:
            return self.extra[path]
        payload = json.loads(stdin) if stdin else {}
        method = args[args.index("--method") + 1]
        parts = path.split("/")
        if parts[-1] == "issues" and method == "POST":
            number = max(self.issues, default=0) + 1
            self.issues[number] = {"number": number, "state": "open", **payload}
            return {"number": number}
        if parts[-1] == "comments" and method == "POST":
            self.comments.setdefault(int(parts[-2]), []).append(payload)
            return {"id": 1}
        self.issues[int(parts[-1])].update(payload)
        return {}

    def probe(self, *a, **k):  # pragma: no cover - interface completeness only
        raise AssertionError("not used")

    def survey(self, *a, **k):  # pragma: no cover - interface completeness only
        raise AssertionError("not used")


def tracker(forge: FakeForge) -> TrackingIssue:
    return TrackingIssue(transport=forge, repository=lambda: REPO)


def test_the_fake_is_a_transport_and_the_tracker_honours_its_interface():
    forge = FakeForge()
    assert isinstance(forge, GhTransportInterface)
    assert isinstance(tracker(forge), TrackingIssueInterface)
    assert isinstance(TrackingIssue(), TrackingIssueInterface)


def test_raising_opens_one_issue_then_updates_it_in_place():
    forge = FakeForge()
    number, created = tracker(forge).raise_issue("k", "first", "body one", labels=["red"])
    assert (number, created) == (1, True)
    assert forge.issues[1]["labels"] == ["red"]
    assert forge.issues[1]["body"].startswith(TrackingIssue.marker("k"))
    again, created = tracker(forge).raise_issue("k", "second", "body two")
    assert (again, created) == (1, False)
    assert forge.issues[1]["title"] == "second" and "body two" in forge.issues[1]["body"]
    assert len(forge.issues) == 1


def test_no_labels_are_sent_unless_declared():
    forge = FakeForge()
    tracker(forge).raise_issue("k", "t", "b")
    assert "labels" not in forge.issues[1]


def test_issues_and_pull_requests_for_other_conditions_are_never_matched():
    forge = FakeForge()
    forge.issues[5] = {"number": 5, "state": "open", "body": TrackingIssue.marker("other")}
    forge.issues[6] = {
        "number": 6,
        "state": "open",
        "body": TrackingIssue.marker("k"),
        "pull_request": {},
    }
    forge.issues[7] = {"number": 7, "state": "open", "body": None}
    assert tracker(forge).find("k") is None


def test_the_oldest_matching_issue_wins_if_a_race_ever_opened_two():
    forge = FakeForge()
    for number in (9, 4):
        forge.issues[number] = {
            "number": number,
            "state": "open",
            "body": TrackingIssue.marker("k"),
        }
    assert tracker(forge).find("k") == 4


def test_an_event_is_commented_once_however_often_it_is_replayed():
    forge = FakeForge()
    for _ in range(3):
        tracker(forge).raise_issue("k", "t", "b", event="red at abc", event_key="run-1")
    tracker(forge).raise_issue("k", "t", "b", event="red at def", event_key="run-2")
    tracker(forge).raise_issue("k", "t", "b", event="ignored without a key")
    bodies = [c["body"] for c in forge.comments[1]]
    assert len(bodies) == 2
    assert "red at abc" in bodies[0] and "run-1" in bodies[0]
    assert "red at def" in bodies[1]


def test_resolving_comments_and_closes_the_open_issue():
    forge = FakeForge()
    tracker(forge).raise_issue("k", "t", "b")
    assert tracker(forge).resolve("k", "green again") == 1
    assert forge.issues[1]["state"] == "closed"
    assert forge.issues[1]["state_reason"] == "completed"
    assert forge.comments[1][-1]["body"] == "green again"
    # Nothing left open: resolving again is a no-op that says so.
    assert tracker(forge).resolve("k", "again") is None


def test_a_listing_the_forge_refused_raises_rather_than_opening_a_duplicate():
    forge = FakeForge()
    forge.fail = "issues?state=open"
    with pytest.raises(RuntimeError, match="HTTP 502"):
        tracker(forge).raise_issue("k", "t", "b")
    assert forge.issues == {}


def test_a_paginated_listing_that_is_not_an_array_is_refused():
    with pytest.raises(TypeError, match="JSON array"):
        TrackingIssue.decode_pages('{"jobs": []}')
    assert TrackingIssue.decode_pages(' [ {"a": 1}, 2 ]\n[{"b": 2}] ') == [{"a": 1}, {"b": 2}]
    assert TrackingIssue.decode_pages("") == []


# ---------------------------------------------------------------------------- command


def test_the_cli_raises_and_resolves_through_the_class(monkeypatch, capsys):
    forge = FakeForge()
    monkeypatch.setattr("vibey_gh.tracking_issue.GhTransport", lambda: forge)
    monkeypatch.setenv("GH_REPO", REPO)
    assert (
        cli.main(
            [
                "tracking-issue",
                "raise",
                "--key",
                "k",
                "--title",
                "T",
                "--body",
                "B",
                "--event",
                "E",
                "--event-key",
                "e1",
                "--label",
                "x",
            ]
        )
        == 0
    )
    assert "opened #1 for k" in capsys.readouterr().out
    assert cli.main(["tracking-issue", "raise", "--key", "k", "--title", "T", "--body", "B"]) == 0
    assert "updated #1 for k" in capsys.readouterr().out
    assert cli.main(["tracking-issue", "resolve", "--key", "k", "--comment", "done"]) == 0
    assert "closed #1 for k" in capsys.readouterr().out
    assert cli.main(["tracking-issue", "resolve", "--key", "k", "--comment", "done"]) == 0
    assert "nothing open for k" in capsys.readouterr().out
    forge.fail = "issues?state=open"
    assert cli.main(["tracking-issue", "resolve", "--key", "k", "--comment", "done"]) == 1
    assert "HTTP 502" in capsys.readouterr().out
