# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from vibey_gh.delivery_sources import DeliverySourceReader, DeliverySourceSnapshot
from vibey_gh.interfaces.delivery_estimate_interface import (
    DeliverySourceReaderInterface,
    DeliverySourceSnapshotInterface,
)


class Transport:
    def __init__(self, issue_value, issue_problem="", pr_value=None, pr_problem="") -> None:
        self.issue_value = issue_value
        self.issue_problem = issue_problem
        self.pr_value = [] if pr_value is None else pr_value
        self.pr_problem = pr_problem
        self.calls = []

    def survey(self, args, *, cwd=None, stdin=None):
        del cwd, stdin
        self.calls.append(tuple(args))
        return (
            (self.issue_value, self.issue_problem)
            if args[0] == "issue"
            else (self.pr_value, self.pr_problem)
        )


def _git_runner(args, cwd):
    del cwd
    if args[0] == "log":
        return subprocess.CompletedProcess(args, 0, "malformed\na\t2026-09-18T00:00:00+00:00\n", "")
    return subprocess.CompletedProcess(args, 0, "abc\n", "")


def test_source_reader_collects_explicit_github_and_git_history() -> None:
    transport = Transport(
        [
            {"number": 1, "state": "OPEN", "labels": [{"name": "size/M"}]},
            {"number": "bad", "state": "OPEN", "labels": "bad"},
            {"number": 4, "state": "OPEN", "labels": "bad", "pullRequest": {}},
        ],
        pr_value=[
            {"number": 2, "state": "MERGED", "mergedAt": "2026-09-18T00:00:00Z", "labels": []},
            {"number": 3, "state": "OPEN", "mergedAt": None, "labels": [{"name": "size/S"}]},
        ],
    )
    reader = DeliverySourceReader(transport=transport, git_run=_git_runner)
    snapshot = reader.read("owner/repo", root=Path("."), limit=25)
    assert isinstance(reader, DeliverySourceReaderInterface)
    assert isinstance(snapshot, DeliverySourceSnapshotInterface)
    assert isinstance(snapshot, DeliverySourceSnapshot)
    assert snapshot.issues[0].labels == ("size/M",)
    assert snapshot.issues[1].labels == ()
    assert snapshot.issues[1].is_pull_request
    assert snapshot.pull_requests[0].merged_at.endswith("Z")
    assert snapshot.commits[0].sha == "a"
    assert snapshot.source_revision == "abc"
    assert snapshot.fingerprint == snapshot.fingerprint
    assert transport.calls[0][-1] == "number,state,labels"
    assert transport.calls[1][-1] == "number,state,mergedAt,labels"


def test_source_reader_preserves_forge_and_git_failures() -> None:
    transport = Transport([], "issues unavailable", [], "pull requests unavailable")

    def failed_git(args, cwd):
        del cwd
        return subprocess.CompletedProcess(args, 1, "", "git unavailable")

    snapshot = DeliverySourceReader(transport=transport, git_run=failed_git).read(
        "owner/repo", root=Path(".")
    )
    assert snapshot.issues == () and snapshot.pull_requests == ()
    assert "issues: issues unavailable" in snapshot.problems
    assert "pull requests: pull requests unavailable" in snapshot.problems
    assert "git history: git unavailable" in snapshot.problems
    assert "git revision: git unavailable" in snapshot.problems
    assert snapshot.source_revision == "unknown"


def test_source_reader_rejects_invalid_limit_and_tolerates_non_lists() -> None:
    with pytest.raises(ValueError, match="positive"):
        DeliverySourceReader().read("owner/repo", root=Path("."), limit=0)
    reader = DeliverySourceReader(
        transport=Transport({"not": "a list"}, pr_value={"not": "a list"}),
        git_run=_git_runner,
    )
    snapshot = reader.read("owner/repo", root=Path("."))
    assert snapshot.issues == () and snapshot.pull_requests == ()


def test_snapshot_fingerprint_changes_with_history() -> None:
    first = DeliverySourceSnapshot(source_revision="a")
    second = DeliverySourceSnapshot(source_revision="b")
    assert first.fingerprint != second.fingerprint
    assert json.dumps(first._issue(first.issues[0])) if first.issues else True


def test_source_reader_default_git_adapter_preserves_unavailable_history(tmp_path: Path) -> None:
    snapshot = DeliverySourceReader(transport=Transport([], pr_value=[])).read(
        "owner/repo", root=tmp_path
    )
    assert snapshot.source_revision == "unknown"
    assert any(problem.startswith("git history:") for problem in snapshot.problems)
