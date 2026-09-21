# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh forge-snapshot`: every class captured, chained, resumable, and honest about gaps.

No test here leaves the machine. `World` is a small GitHub: it holds a repository's issues,
comments, pull requests, reviews, review comments, labels, milestones, releases and tags as
the REST API returns them, and scripts the `fake_gh` on PATH (`conftest.FakeGh`) with the
exact command lines a capture makes, filtered and paged the way GitHub filters and pages.
The code under test therefore runs real processes with real argv, and a wrong path, a
missing `--slurp` or a lost `since` is an unscripted call that fails the test.

The chain is verified here independently of the code that wrote it: `verify` recomputes
every digest from the bytes on disk with nothing but `hashlib` and `json`, so the property
is proven, not echoed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import github_state
from vibey_gh.cli import main
from vibey_gh.forge_snapshot import (
    CLASSES,
    EXCLUDED,
    MANIFEST_NAME,
    MANIFEST_SCHEMA,
    RECORD_SCHEMA,
    ForgeClass,
    ForgeSnapshot,
    GithubForgeReader,
    JsonlSnapshotStore,
    SnapshotStoreError,
    canonical_bytes,
    digest,
    moment,
    stamp,
)
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_snapshot_interface import (
    ChainHead,
    ForgeRead,
    ForgeReaderInterface,
    ForgeSnapshotInterface,
    SnapshotStoreInterface,
)

REPO = "acme/widgets"
API = "https://api.github.com/repos/acme/widgets"
NAMES = tuple(spec.name for spec in CLASSES)


def user(login: str, uid: int) -> dict[str, Any]:
    return {
        "login": login,
        "id": uid,
        "node_id": f"U_{uid}",
        "type": "User",
        "site_admin": False,
        "html_url": f"https://github.com/{login}",
    }


def reactions(url: str, **counts: int) -> dict[str, Any]:
    base = {k: 0 for k in ("+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes")}
    base.update(counts)
    return {"url": f"{url}/reactions", "total_count": sum(base.values()), **base}


@dataclass
class World:
    """A GitHub repository's REST-visible state, scripted into `fake_gh` as GitHub serves it."""

    per_page: int = 100
    issues: list[dict[str, Any]] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    pulls: list[dict[str, Any]] = field(default_factory=list)
    reviews: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    review_comments: list[dict[str, Any]] = field(default_factory=list)
    labels: list[dict[str, Any]] = field(default_factory=list)
    milestones: list[dict[str, Any]] = field(default_factory=list)
    releases: list[dict[str, Any]] = field(default_factory=list)
    tags: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def seeded(cls, per_page: int = 100) -> World:
        world = cls(per_page=per_page)
        ada, bo = user("ada", 1), user("bo", 2)
        bug = {
            "id": 101,
            "node_id": "LA_101",
            "name": "bug",
            "color": "d73a4a",
            "default": True,
            "description": "Something is broken",
            "url": f"{API}/labels/bug",
        }
        docs = {
            "id": 102,
            "node_id": "LA_102",
            "name": "docs",
            "color": "0075ca",
            "default": False,
            "description": "Documentation",
            "url": f"{API}/labels/docs",
        }
        world.labels = [bug, docs]
        world.milestones = [
            {
                "id": 301,
                "node_id": "MI_301",
                "number": 1,
                "title": "1.0",
                "state": "open",
                "description": "First release",
                "creator": ada,
                "open_issues": 1,
                "closed_issues": 0,
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-09-01T09:00:00Z",
                "closed_at": None,
                "due_on": None,
                "url": f"{API}/milestones/1",
            },
        ]
        world.issues = [
            {
                "id": 1001,
                "node_id": "I_1001",
                "number": 1,
                "title": "Crash on start",
                "state": "open",
                "state_reason": None,
                "locked": False,
                "user": ada,
                "labels": [bug],
                "assignees": [bo],
                "milestone": world.milestones[0],
                "comments": 1,
                "body": "It crashes. ✨ Ünïcode survives.",
                "author_association": "OWNER",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T10:00:00Z",
                "closed_at": None,
                "reactions": reactions(f"{API}/issues/1", heart=2),
                "url": f"{API}/issues/1",
            },
            # On GitHub a pull request is also an issue, and the issues listing returns it.
            {
                "id": 1002,
                "node_id": "I_1002",
                "number": 2,
                "title": "Fix the crash",
                "state": "closed",
                "state_reason": None,
                "locked": False,
                "user": bo,
                "labels": [],
                "assignees": [],
                "milestone": None,
                "comments": 0,
                "body": "Fixes #1",
                "author_association": "CONTRIBUTOR",
                "created_at": "2026-09-02T08:00:00Z",
                "updated_at": "2026-09-02T12:00:00Z",
                "closed_at": "2026-09-02T12:00:00Z",
                "pull_request": {"url": f"{API}/pulls/2", "merged_at": "2026-09-02T12:00:00Z"},
                "reactions": reactions(f"{API}/issues/2"),
                "url": f"{API}/issues/2",
            },
        ]
        world.comments = [
            {
                "id": 5001,
                "node_id": "IC_5001",
                "user": bo,
                "body": "Seen it too.",
                "author_association": "CONTRIBUTOR",
                "created_at": "2026-09-01T09:30:00Z",
                "updated_at": "2026-09-01T09:30:00Z",
                "issue_url": f"{API}/issues/1",
                "reactions": reactions(f"{API}/issues/comments/5001"),
                "url": f"{API}/issues/comments/5001",
            },
        ]
        world.pulls = [
            {
                "id": 2002,
                "node_id": "PR_2002",
                "number": 2,
                "title": "Fix the crash",
                "state": "closed",
                "draft": False,
                "locked": False,
                "user": bo,
                "body": "Fixes #1",
                "labels": [],
                "requested_reviewers": [],
                "requested_teams": [],
                "head": {"ref": "fix/crash", "sha": "a" * 40},
                "base": {"ref": "develop", "sha": "b" * 40},
                "merge_commit_sha": "c" * 40,
                "author_association": "CONTRIBUTOR",
                "created_at": "2026-09-02T08:00:00Z",
                "updated_at": "2026-09-02T12:00:00Z",
                "closed_at": "2026-09-02T12:00:00Z",
                "merged_at": "2026-09-02T12:00:00Z",
                "url": f"{API}/pulls/2",
            },
        ]
        world.reviews = {
            2: [
                {
                    "id": 7001,
                    "node_id": "PRR_7001",
                    "user": ada,
                    "body": "Looks right.",
                    "state": "APPROVED",
                    "commit_id": "a" * 40,
                    "author_association": "OWNER",
                    "submitted_at": "2026-09-02T11:00:00Z",
                    "pull_request_url": f"{API}/pulls/2",
                },
            ]
        }
        world.review_comments = [
            {
                "id": 8001,
                "node_id": "PRRC_8001",
                "pull_request_review_id": 7001,
                "user": ada,
                "body": "nit: name this",
                "path": "src/app.py",
                "line": 12,
                "side": "RIGHT",
                "commit_id": "a" * 40,
                "diff_hunk": "@@ -1 +1 @@",
                "in_reply_to_id": None,
                "created_at": "2026-09-02T11:00:00Z",
                "updated_at": "2026-09-02T11:00:00Z",
                "reactions": reactions(f"{API}/pulls/comments/8001"),
                "pull_request_url": f"{API}/pulls/2",
                "url": f"{API}/pulls/comments/8001",
            },
        ]
        world.releases = [
            {
                "id": 9001,
                "node_id": "RE_9001",
                "tag_name": "v1.0.0",
                "name": "1.0.0",
                "draft": False,
                "prerelease": False,
                "author": ada,
                "body": "First.",
                "target_commitish": "main",
                "created_at": "2026-09-03T00:00:00Z",
                "published_at": "2026-09-03T00:05:00Z",
                "url": f"{API}/releases/9001",
                "assets": [
                    {
                        "id": 9101,
                        "name": "widgets-1.0.0.tar.gz",
                        "label": "",
                        "state": "uploaded",
                        "content_type": "application/gzip",
                        "size": 20480,
                        "download_count": 3,
                        "digest": "sha256:" + "d" * 64,
                        "uploader": ada,
                        "created_at": "2026-09-03T00:04:00Z",
                        "updated_at": "2026-09-03T00:04:30Z",
                        "browser_download_url": "https://github.com/acme/widgets/releases/download/"
                        "v1.0.0/widgets-1.0.0.tar.gz",
                    },
                ],
            },
        ]
        world.tags = [
            {
                "name": "v1.0.0",
                "node_id": "REF_v1",
                "commit": {"sha": "c" * 40, "url": f"{API}/commits/{'c' * 40}"},
                "zipball_url": f"{API}/zipball/refs/tags/v1.0.0",
                "tarball_url": f"{API}/tarball/refs/tags/v1.0.0",
            },
        ]
        return world

    # -- the command lines a capture makes -------------------------------------------------

    def path(self, name: str, since: str | None = None, **extra: Any) -> str:
        spec = ForgeClass.named(name)
        text = spec.endpoint.format(repository=REPO, per_page=self.per_page, **extra)
        return f"{text}&since={since}" if spec.since and since is not None else text

    @staticmethod
    def listing(path: str) -> str:
        return f"api {path} --paginate --slurp"

    def page(self, number: int) -> str:
        return f"api {self.path('change-request')}&page={number}"

    # -- how GitHub answers them ---------------------------------------------------------

    def _pages(self, items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        chunks = [items[i : i + self.per_page] for i in range(0, len(items), self.per_page)]
        return chunks or [[]]

    @staticmethod
    def _since(items: Iterable[dict[str, Any]], since: str | None) -> list[dict[str, Any]]:
        chosen = [i for i in items if since is None or moment(i["updated_at"]) >= moment(since)]
        return sorted(chosen, key=lambda i: i["updated_at"])

    def answers(self, *sinces: str | None) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for since in sinces or (None,):
            for name, items in (
                ("issue", self.issues),
                ("comment", self.comments),
                ("review-comment", self.review_comments),
            ):
                pages = self._pages(self._since(items, since))
                out[self.listing(self.path(name, since))] = {"out": json.dumps(pages)}
        for name, items in (
            ("label", self.labels),
            ("milestone", self.milestones),
            ("release", self.releases),
            ("tag", self.tags),
        ):
            out[self.listing(self.path(name))] = {"out": json.dumps(self._pages(items))}
        ordered = sorted(self.pulls, key=lambda p: str(p["updated_at"] or ""), reverse=True)
        pages = [ordered[i : i + self.per_page] for i in range(0, len(ordered), self.per_page)]
        for number, page in enumerate([*pages, []], start=1):
            out[self.page(number)] = {"out": json.dumps(page)}
        for pull in self.pulls:
            reviews = self._pages(self.reviews.get(pull["number"], []))
            out[self.listing(self.path("review", number=pull["number"]))] = {
                "out": json.dumps(reviews)
            }
        return out


class Ticks:
    """A clock that moves one second per reading, from a fixed moment."""

    def __init__(self, start: str = "2026-09-10T00:00:00Z") -> None:
        self.now = moment(start)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def snap(tmp_path: Path) -> Path:
    """The snapshot directory: beside `fake_gh`'s `bin/`, never the same directory."""
    return tmp_path / "snap"


def snapshot(out: Path, *, per_page: int = 100, clock: Ticks | None = None) -> ForgeSnapshot:
    reader = GithubForgeReader(GhTransport(), REPO, per_page=per_page)
    store = JsonlSnapshotStore(out, forge=reader.forge, repository=reader.repository)
    return ForgeSnapshot(reader, store, clock=clock or Ticks())


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def verify(path: Path) -> str | None:
    """Recompute a class file's chain from its bytes alone; return the head, or raise."""
    head: str | None = None
    for number, raw in enumerate(path.read_bytes().splitlines(), start=1):
        record = json.loads(raw)
        sealed = record.pop("sha256")
        body = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        # The bytes on disk ARE the canonical form, so the body re-serialises to them.
        rendered = json.dumps({**record, "sha256": sealed}, sort_keys=True, separators=(",", ":"))
        assert rendered.encode() == raw, f"line {number} is not in canonical form"
        assert hashlib.sha256(body).hexdigest() == sealed, f"line {number} does not match its seal"
        content = json.dumps(record["payload"], sort_keys=True, separators=(",", ":")).encode()
        assert hashlib.sha256(content).hexdigest() == record["payload_sha256"]
        assert record["prev"] == head, f"line {number} does not link to the line before it"
        head = sealed
    return head


# -- a full capture ------------------------------------------------------------------------


def test_a_full_capture_writes_every_class_verbatim_and_chained(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers())
    manifest = snapshot(snap).capture()

    assert manifest["schema"] == MANIFEST_SCHEMA and manifest["record_schema"] == RECORD_SCHEMA
    assert (manifest["forge"], manifest["repository"]) == ("github", REPO)
    assert manifest["complete"] is True and manifest["since"] is None
    expected = {
        "issue": world.issues,
        "comment": world.comments,
        "change-request": world.pulls,
        "review": world.reviews[2],
        "review-comment": world.review_comments,
        "label": world.labels,
        "milestone": world.milestones,
        "release": world.releases,
        "tag": world.tags,
    }
    for name, items in expected.items():
        spec = ForgeClass.named(name)
        records = lines(snap / f"{name}.jsonl")
        # Verbatim: the payload is the forge's JSON, every field, unicode and all.
        assert [r["payload"] for r in records] == sorted(
            items, key=lambda i: str(i.get("updated_at", ""))
        ) or [r["payload"] for r in records] == items
        assert {r["native_id"] for r in records} == {str(i[spec.id_field]) for i in items}
        assert all(r["class"] == name and r["native_class"] == spec.native_class for r in records)
        entry = manifest["classes"][name]
        assert entry["status"] == "captured" and entry["problem"] == ""
        assert entry["observed"] == entry["appended"] == entry["records"] == len(items)
        assert entry["head"] == verify(snap / f"{name}.jsonl")
    # The issue side of a pull request is kept, and says what it is.
    assert any("pull_request" in r["payload"] for r in lines(snap / "issue.jsonl"))
    # Tags have no numeric id; their name is theirs.
    assert lines(snap / "tag.jsonl")[0]["native_id"] == "v1.0.0"
    # The asset manifest rides inside the release, verbatim.
    assert lines(snap / "release.jsonl")[0]["payload"]["assets"][0]["size"] == 20480
    # The forge's latest update is 2026-09-02; the capture began at 2026-09-10T00:00:01Z by
    # this machine's clock. Nothing can have been missed up to five minutes before that.
    cursors = {n: e["cursor"] for n, e in manifest["classes"].items()}
    floor = "2026-09-09T23:55:01Z"
    assert cursors == {
        "issue": floor,
        "comment": floor,
        "change-request": floor,
        "review": floor,
        "review-comment": floor,
        "label": None,
        "milestone": None,
        "release": None,
        "tag": None,
    }
    assert manifest["resume_since"] == floor
    assert manifest["clock_skew_seconds"] == 300
    assert json.loads((snap / MANIFEST_NAME).read_text(encoding="utf-8")) == manifest
    assert not (snap / f"{MANIFEST_NAME}.partial").exists()
    # Read-only: every call a capture made is a GET listing, nothing else.
    assert all(call.startswith("api repos/acme/widgets/") for call in fake_gh.calls())
    assert not any("--method" in call or " -f " in call for call in fake_gh.calls())


def test_a_capture_repeated_over_the_same_moment_appends_nothing(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers())
    first = snapshot(snap).capture()
    before = {name: (snap / f"{name}.jsonl").read_bytes() for name in NAMES}
    second = snapshot(snap).capture()
    for name in NAMES:
        assert (snap / f"{name}.jsonl").read_bytes() == before[name]
        entry = second["classes"][name]
        assert entry["appended"] == 0 and entry["unchanged"] == entry["observed"]
        assert entry["head"] == first["classes"][name]["head"]


# -- the chain -----------------------------------------------------------------------------


def test_the_chain_exposes_an_edited_a_removed_and_a_reordered_line(fake_gh, snap):
    world = World.seeded()
    world.labels.append({**world.labels[0], "id": 103, "name": "third"})
    fake_gh.script(world.answers())
    snapshot(snap).capture(classes=["label"])
    path = snap / "label.jsonl"
    original = path.read_bytes().splitlines(keepends=True)
    assert len(original) == 3 and verify(path)

    edited = json.loads(original[1])
    edited["payload"]["name"] = "forged"
    tampered = json.dumps(edited, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    for broken in (
        [original[0], tampered, original[2]],  # a line's content changed
        [original[0], original[2]],  # a line removed
        [original[1], original[0], original[2]],  # two lines swapped
    ):
        path.write_bytes(b"".join(broken))
        with pytest.raises(AssertionError):
            verify(path)


@pytest.mark.parametrize("tamper", ("canonical", "record", "payload", "previous"))
def test_the_store_refuses_a_tampered_chain_before_reading_the_forge(fake_gh, snap, tamper):
    world = World.seeded()
    world.labels.append({**world.labels[0], "id": 103, "name": "third"})
    fake_gh.script(world.answers())
    snapshot(snap).capture(classes=["label"])
    path = snap / "label.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    if tamper == "canonical":
        raw_lines = path.read_bytes().splitlines(keepends=True)
        raw_lines[1] = raw_lines[1].removesuffix(b"\n") + b" \n"
        path.write_bytes(b"".join(raw_lines))
    else:
        record = records[1]
        if tamper == "record":
            record["sha256"] = "0" * 64
        elif tamper == "payload":
            record["payload"]["name"] = "forged"
            record.pop("sha256")
            record["sha256"] = digest(record)
        else:
            record["prev"] = "0" * 64
            record.pop("sha256")
            record["sha256"] = digest(record)
        records[1] = record
        path.write_bytes(b"".join(canonical_bytes(item) + b"\n" for item in records))

    fake_gh.forget()
    with pytest.raises(SnapshotStoreError, match=r"label\.jsonl line 2"):
        JsonlSnapshotStore(snap, forge="github", repository=REPO).chain("label")
    assert fake_gh.calls() == []


def test_the_canonical_form_is_the_ledgers_and_stable():
    record = {"b": [1, {"z": None, "a": "é✨"}], "a": True}
    assert canonical_bytes(record) == b'{"a":true,"b":[1,{"a":"\\u00e9\\u2728","z":null}]}'
    assert canonical_bytes(record) == canonical_bytes(dict(reversed(list(record.items()))))
    # A golden value: if this moves, every record ever sealed stops verifying.
    assert digest(record) == hashlib.sha256(canonical_bytes(record)).hexdigest()
    assert digest(record) == "db6424cb96e5f75d4faa72e153d8858e8c3417163a7d6430b400391814635a2f"


def test_the_canonical_form_matches_vibeys_ledger_byte_for_byte():
    ledger = pytest.importorskip("vibey.domain.ledger")
    for value in ({"b": 1, "a": [None, "é", 2.5]}, {"payload": {"✨": {"x": [True]}}}, {}):
        assert canonical_bytes(value) == ledger.canonical_bytes(value)
        assert digest(value) == ledger.digest_event(value)


def test_moments_are_written_the_way_github_writes_them():
    assert stamp(moment("2026-09-18")) == "2026-09-18T00:00:00Z"
    assert stamp(moment("2026-09-18T12:30:45.9+02:00")) == "2026-09-18T10:30:45Z"
    assert stamp(datetime(2026, 9, 18, tzinfo=UTC)) == "2026-09-18T00:00:00Z"
    with pytest.raises(ValueError):
        moment("yesterday")


# -- could not look ------------------------------------------------------------------------


def test_a_class_that_could_not_be_looked_at_is_recorded_never_written_as_empty(fake_gh, snap):
    world = World.seeded()
    world.milestones = []
    answers = world.answers()
    answers[World.listing(world.path("comment"))] = {"err": "HTTP 502: Bad Gateway\n", "code": 1}
    answers[World.listing(world.path("label"))] = {"out": "<html>not json</html>"}
    answers[World.listing(world.path("tag"))] = {"out": json.dumps({"message": "Not Found"})}
    answers[World.listing(world.path("release"))] = {"out": json.dumps([[1, 2]])}
    fake_gh.script(answers)
    manifest = snapshot(snap).capture()

    assert manifest["complete"] is False
    problems = {n: e["problem"] for n, e in manifest["classes"].items() if e["problem"]}
    assert problems == {
        "comment": f"`gh api {world.path('comment')}` failed: HTTP 502: Bad Gateway",
        "label": f"`gh api {world.path('label')}` returned output that is not JSON",
        "tag": f"`api {world.path('tag')}` did not answer with a list of pages",
        "release": f"`api {world.path('release')}` listed something that is not a JSON object",
    }
    for name in problems:
        entry = manifest["classes"][name]
        assert entry["status"] == "could-not-look"
        assert entry["observed"] is None and entry["appended"] == 0 and entry["cursor"] is None
        assert not (snap / f"{name}.jsonl").exists()
    # Looked, and found nothing, is a different fact, and reads as one.
    empty = manifest["classes"]["milestone"]
    assert (empty["status"], empty["observed"], empty["records"]) == ("captured", 0, 0)
    assert not (snap / "milestone.jsonl").exists()
    # A resumable class that could not look holds the resume point back.
    assert manifest["resume_since"] is None
    assert manifest["classes"]["issue"]["status"] == "captured"


def test_a_missing_client_is_a_class_it_could_not_look_at(tmp_path):
    reader = GithubForgeReader(GhTransport(executable="gh-is-not-installed-here"), REPO)
    store = JsonlSnapshotStore(tmp_path, forge=reader.forge, repository=REPO)
    manifest = ForgeSnapshot(reader, store, clock=Ticks()).capture(classes=["issue", "review"])
    assert manifest["complete"] is False
    assert manifest["classes"]["issue"]["problem"] == (
        "the GitHub CLI (`gh-is-not-installed-here`) is not installed"
    )
    assert manifest["classes"]["review"]["problem"] == (
        "the change requests these reviews belong to could not be listed:"
        " the GitHub CLI (`gh-is-not-installed-here`) is not installed"
    )
    assert sorted(p.name for p in tmp_path.iterdir()) == [MANIFEST_NAME]


def test_a_review_listing_that_fails_holds_back_only_the_reviews(fake_gh, snap):
    world = World.seeded()
    answers = world.answers()
    answers[World.listing(world.path("review", number=2))] = {"err": "HTTP 403\n", "code": 1}
    fake_gh.script(answers)
    manifest = snapshot(snap).capture(classes=["change-request", "review"])
    assert manifest["classes"]["change-request"]["status"] == "captured"
    assert manifest["classes"]["review"]["status"] == "could-not-look"
    assert manifest["classes"]["review"]["problem"].endswith("failed: HTTP 403")
    assert not (snap / "review.jsonl").exists()
    # One walk of the change requests served both classes.
    assert sum(call.startswith("api repos/acme/widgets/pulls?") for call in fake_gh.calls()) == 1


def test_a_change_request_page_that_fails_or_is_malformed_is_reported(fake_gh, snap):
    world = World.seeded()
    answers = world.answers()
    answers[world.page(1)] = {"err": "HTTP 500\n", "code": 1}
    fake_gh.script(answers)
    failed = snapshot(snap / "a").capture(classes=["change-request"])
    assert failed["classes"]["change-request"]["problem"].endswith("failed: HTTP 500")

    answers[world.page(1)] = {"out": json.dumps({"message": "Moved"})}
    fake_gh.script(answers)
    shaped = snapshot(snap / "b").capture(classes=["change-request"])
    assert shaped["classes"]["change-request"]["problem"] == (
        f"`api {world.page(1)[4:]}` did not answer with a list of JSON objects"
    )


def test_items_the_forge_cannot_identify_are_refused_not_guessed(fake_gh, snap):
    world = World.seeded()
    world.labels.append({"name": "no-id"})
    world.tags.append({"name": True})
    world.pulls.append(
        {**world.pulls[0], "id": 2003, "number": None, "updated_at": "2026-09-01T00:00:00Z"}
    )
    fake_gh.script(world.answers())
    manifest = snapshot(snap).capture(classes=["label", "tag", "review"])
    assert manifest["classes"]["label"]["problem"] == "the forge listed a label with no `id`"
    assert manifest["classes"]["tag"]["problem"] == "the forge listed a tag with no `name`"
    assert manifest["classes"]["review"]["problem"] == (
        "change request 2003 has no number to list its reviews by"
    )


# -- resuming ------------------------------------------------------------------------------


def test_a_capture_resumes_from_its_cursor_and_continues_every_chain(fake_gh, snap):
    world = World.seeded()
    # One comment edited inside the clock-skew allowance: its update time is the forge's
    # latest, so it, and not the machine's clock, sets the comment cursor.
    world.comments.append({**world.comments[0], "id": 5003, "updated_at": "2026-09-09T23:58:00Z"})
    fake_gh.script(world.answers())
    first = snapshot(snap).capture()
    heads = {name: first["classes"][name]["head"] for name in NAMES}
    assert first["classes"]["comment"]["cursor"] == "2026-09-09T23:58:00Z"
    resume = first["resume_since"]
    assert resume == "2026-09-09T23:55:01Z"

    # A day on the forge: an issue edited, a comment added, the pull request reviewed again
    # (which updates it), a label renamed. Everything else is exactly as it was.
    world.issues[0] = {
        **world.issues[0],
        "title": "Crash on start (macOS)",
        "updated_at": "2026-09-10T10:00:00Z",
    }
    world.comments.append(
        {
            **world.comments[0],
            "id": 5002,
            "body": "Fixed for me.",
            "created_at": "2026-09-10T11:00:00Z",
            "updated_at": "2026-09-10T11:00:00Z",
        }
    )
    world.pulls[0] = {**world.pulls[0], "updated_at": "2026-09-10T12:00:00Z"}
    world.reviews[2].append(
        {
            **world.reviews[2][0],
            "id": 7002,
            "body": "Post-merge: +1",
            "state": "COMMENTED",
            "submitted_at": "2026-09-10T12:00:00Z",
        }
    )
    world.labels[1] = {**world.labels[1], "name": "documentation"}
    fake_gh.script(world.answers(resume))
    fake_gh.forget()
    second = snapshot(snap, clock=Ticks("2026-09-11T00:00:00Z")).capture(since="resume")

    assert second["since"] == resume and second["complete"] is True
    # The since-filtered endpoints were asked from the cursor, not from the beginning.
    calls = fake_gh.calls()
    for name in ("issue", "comment", "review-comment"):
        assert World.listing(world.path(name, resume)) in calls
    observed = {
        n: (e["observed"], e["appended"], e["unchanged"]) for n, e in second["classes"].items()
    }
    assert observed == {
        "issue": (1, 1, 0),
        "comment": (2, 1, 1),  # the new comment, and the one inside the overlap, unchanged
        "change-request": (1, 1, 0),
        "review": (2, 1, 1),  # the change request's new review, and its old one unchanged
        "review-comment": (0, 0, 0),
        "label": (2, 1, 1),
        "milestone": (1, 0, 1),
        "release": (1, 0, 1),
        "tag": (1, 0, 1),
    }
    for name in NAMES:
        records = lines(snap / f"{name}.jsonl")
        appended = second["classes"][name]["appended"]
        if appended:
            # The first record this capture wrote links to the last one the previous wrote.
            assert records[-appended]["prev"] == heads[name]
        assert verify(snap / f"{name}.jsonl") == second["classes"][name]["head"]
    # Point in time: both versions of the edited issue are there, each with its moment.
    versions = [r for r in lines(snap / "issue.jsonl") if r["native_id"] == "1001"]
    assert [v["payload"]["title"] for v in versions] == ["Crash on start", "Crash on start (macOS)"]
    assert versions[0]["captured_at"] < versions[1]["captured_at"]
    assert second["resume_since"] == "2026-09-10T23:55:01Z"


def test_the_change_request_walk_stops_at_the_cursor(fake_gh, snap):
    world = World.seeded(per_page=2)
    template = world.pulls[0]
    world.pulls = [
        {**template, "id": 2100 + n, "number": 100 + n, "updated_at": f"2026-09-0{n}T00:00:00Z"}
        for n in range(1, 7)
    ]
    fake_gh.script(world.answers())
    manifest = snapshot(snap, per_page=2).capture(
        classes=["change-request"], since="2026-09-04T00:00:00Z"
    )
    entry = manifest["classes"]["change-request"]
    # Three observed; and no cursor, because everything before the moment was never walked.
    assert (entry["observed"], entry["cursor"]) == (3, None)
    assert [c for c in fake_gh.calls() if "pulls?" in c] == [world.page(1), world.page(2)]
    ids = [r["native_id"] for r in lines(snap / "change-request.jsonl")]
    assert ids == ["2106", "2105", "2104"]

    fake_gh.forget()
    full = snapshot(snap / "full", per_page=2).capture(classes=["change-request"])
    assert full["classes"]["change-request"]["observed"] == 6
    assert [c for c in fake_gh.calls() if "pulls?" in c] == [world.page(n) for n in (1, 2, 3, 4)]


def test_a_capture_from_past_the_cursor_leaves_the_gap_for_resume_to_fill(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers(None, "2026-09-20T00:00:00Z", "2026-09-01T00:00:00Z"))
    first = snapshot(snap).capture(classes=["issue"])
    assert first["classes"]["issue"]["cursor"] == "2026-09-09T23:55:01Z"
    # Asked to start ten days AFTER the cursor, the capture leaves those ten days unwalked,
    # so the cursor does not move, however late this machine's clock says it is.
    later = snapshot(snap, clock=Ticks("2026-09-30T00:00:00Z")).capture(
        classes=["issue"], since="2026-09-20T00:00:00Z"
    )
    assert later["classes"]["issue"]["cursor"] == "2026-09-09T23:55:01Z"
    # From before the cursor, the walk overlaps what was seen, and the cursor moves on.
    earlier = snapshot(snap, clock=Ticks("2026-09-30T00:00:00Z")).capture(
        classes=["issue"], since="2026-09-01T00:00:00Z"
    )
    assert earlier["classes"]["issue"]["cursor"] == "2026-09-29T23:55:01Z"


def test_an_empty_class_does_not_hold_every_resume_point_back(fake_gh, snap):
    world = World.seeded()
    world.pulls, world.reviews, world.review_comments = [], {}, []
    fake_gh.script(world.answers())
    manifest = snapshot(snap).capture()
    for name in ("change-request", "review", "review-comment"):
        entry = manifest["classes"][name]
        assert (entry["observed"], entry["cursor"]) == (0, "2026-09-09T23:55:01Z")
    assert manifest["resume_since"] == "2026-09-09T23:55:01Z"


def test_update_times_the_forge_did_not_give_do_not_move_a_cursor(fake_gh, snap):
    world = World.seeded()
    world.pulls = [
        {**world.pulls[0], "id": 2201, "number": 21, "updated_at": None},
        {**world.pulls[0], "id": 2202, "number": 22, "updated_at": "not a moment"},
    ]
    fake_gh.script(world.answers())
    after = snapshot(snap / "a").capture(classes=["change-request"], since="2026-09-09T00:00:00Z")
    # Kept, because nothing says they are older than the moment.
    assert after["classes"]["change-request"]["observed"] == 2
    full = snapshot(snap / "b", clock=Ticks("2026-09-10T00:00:00Z")).capture(
        classes=["change-request"]
    )
    # And no cursor is read out of them: only the clock's floor stands.
    assert full["classes"]["change-request"]["cursor"] == "2026-09-09T23:55:01Z"


def test_resume_with_no_resume_point_is_a_full_capture(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers())
    manifest = snapshot(snap).capture(classes=["label"], since="resume")
    assert manifest["since"] is None and manifest["resume_since"] is None
    again = snapshot(snap).capture(classes=["label"], since="resume")
    assert again["since"] is None


def test_classes_not_selected_are_named_and_keep_their_cursors(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers())
    first = snapshot(snap).capture()
    second = snapshot(snap).capture(classes=["label"])
    for name in NAMES:
        entry, before = second["classes"][name], first["classes"][name]
        if name == "label":
            continue
        assert entry["status"] == "not-selected" and entry["captured_at"] is None
        assert (entry["records"], entry["head"], entry["cursor"]) == (
            before["records"],
            before["head"],
            before["cursor"],
        )
    not_selected = [e["class"] for e in second["excluded"] if e["class"] in NAMES]
    assert sorted(not_selected) == sorted(set(NAMES) - {"label"})
    assert second["resume_since"] == first["resume_since"]


def test_a_hand_edited_manifest_cannot_supply_a_cursor(fake_gh, snap):
    world = World.seeded()
    fake_gh.script(world.answers())
    snapshot(snap).capture(classes=["label"])
    path = snap / MANIFEST_NAME
    for classes in (
        [],
        {"issue": "x"},
        {"issue": {"cursor": 7}},
        {"issue": {"cursor": "someday"}},
    ):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["classes"] = classes
        path.write_text(json.dumps(manifest), encoding="utf-8")
        again = snapshot(snap).capture(classes=["label"])
        assert again["classes"]["issue"]["cursor"] is None


# -- refusals ------------------------------------------------------------------------------


def test_selections_and_moments_are_checked_before_anything_is_read(fake_gh, snap):
    capture = snapshot(snap)
    with pytest.raises(ValueError, match="unknown artifact class 'pr'; supported: issue"):
        capture.capture(classes=["pr"])
    with pytest.raises(ValueError, match="no artifact class selected"):
        capture.capture(classes=[])
    with pytest.raises(ValueError, match="not an ISO 8601 moment: 'last week'"):
        capture.capture(since="last week")
    with pytest.raises(ValueError, match="unknown artifact class"):
        GithubForgeReader(GhTransport(), REPO).read("wiki", None)
    assert fake_gh.calls() == [] and not snap.exists()


def test_a_negative_clock_allowance_is_refused(tmp_path):
    reader = GithubForgeReader(GhTransport(), REPO)
    store = JsonlSnapshotStore(tmp_path, forge="github", repository=REPO)
    with pytest.raises(ValueError, match="clock_skew must not be negative"):
        ForgeSnapshot(reader, store, clock_skew=timedelta(seconds=-1))


def test_a_resume_point_that_is_not_a_moment_is_refused(tmp_path):
    (tmp_path / MANIFEST_NAME).write_text(
        json.dumps(
            {
                "schema": MANIFEST_SCHEMA,
                "forge": "github",
                "repository": REPO,
                "resume_since": "resume",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not an ISO 8601 moment: 'resume'"):
        snapshot(tmp_path).capture(since="resume")


@pytest.mark.parametrize(
    ("repository", "per_page", "message"),
    [
        ("widgets", 100, "not an owner/name repository"),
        ("acme/widgets/../../x", 100, "not an owner/name repository"),
        (REPO, 0, "per_page must be between 1 and 100"),
        (REPO, 101, "per_page must be between 1 and 100"),
    ],
)
def test_the_reader_refuses_what_it_cannot_ask_about(repository, per_page, message):
    with pytest.raises(ValueError, match=message):
        GithubForgeReader(GhTransport(), repository, per_page=per_page)


def foreign(**overrides: Any) -> bytes:
    """A line that is almost this store's own label record, but for `overrides`."""
    record = {
        "schema": RECORD_SCHEMA,
        "forge": "github",
        "repository": REPO,
        "class": "label",
        "native_class": "label",
        "native_id": "1",
        "payload_sha256": "x",
        "sha256": "y",
    }
    return json.dumps({**record, **overrides}).encode() + b"\n"


@pytest.mark.parametrize(
    "line",
    [
        b"{not json\n",
        b'{"schema":"vibey.forge-record/1","forge":"github"',  # torn: the write never finished
        b"\xff\xfe\n",  # not UTF-8
        b"[]\n",
        foreign(schema="vibey.forge-record/2"),  # a schema this store does not write
        foreign(repository="other/repo"),  # another repository's chain
        foreign(native_id=1),  # an id that is not a string
    ],
)
def test_a_class_file_this_store_did_not_write_is_refused_whole(fake_gh, snap, line):
    fake_gh.script(World.seeded().answers())
    snapshot(snap).capture(classes=["label"])
    path = snap / "label.jsonl"
    path.write_bytes(path.read_bytes() + line)
    before = {p.name: p.read_bytes() for p in snap.iterdir()}
    fake_gh.forget()
    with pytest.raises(SnapshotStoreError, match=r"label.jsonl line 3 is not a vibey"):
        snapshot(snap).capture(classes=["issue"])
    # Refused before the forge was asked anything, and nothing was written.
    assert fake_gh.calls() == []
    assert {p.name: p.read_bytes() for p in snap.iterdir()} == before


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{nope", "is not JSON"),
        ("[]", "is not a vibey.forge-manifest/1 manifest"),
        (json.dumps({"schema": "other"}), "is not a vibey.forge-manifest/1 manifest"),
        (
            json.dumps({"schema": MANIFEST_SCHEMA, "forge": "github", "repository": "else/where"}),
            "describes github else/where, not github acme/widgets",
        ),
    ],
)
def test_a_manifest_for_something_else_is_refused(tmp_path, text, message):
    (tmp_path / MANIFEST_NAME).write_text(text, encoding="utf-8")
    with pytest.raises(SnapshotStoreError, match=message):
        snapshot(tmp_path).capture()


# -- exclusion honesty ---------------------------------------------------------------------


def test_every_class_the_issue_names_is_captured_or_excluded_with_a_reason():
    captured = {spec.name for spec in CLASSES}
    excluded = [name for name, _reason in EXCLUDED]
    assert len(excluded) == len(set(excluded)), "an excluded class is named twice"
    assert not captured & set(excluded), "a class is both captured and excluded"
    assert all(reason.strip() and reason.endswith(".") for _name, reason in EXCLUDED)
    # vibey#136's own enumeration, in its words, mapped to the names used here.
    named_by_the_issue = {
        "issues": "issue",
        "issue comments": "comment",
        "PR comments": "review-comment",
        "reviews": "review",
        "review threads": "review-thread",
        "timeline events": "timeline-event",
        "labels": "label",
        "milestones": "milestone",
        "releases": "release",
        "asset manifests": "release",
        "check runs": "check-run",
        "statuses": "commit-status",
        "discussions": "discussion",
        "rulesets": "ruleset",
        "branch protections": "branch-protection",
        "repository metadata": "repository-metadata",
        "workflow-run records": "workflow-run",
        "pull requests": "change-request",
        "tags": "tag",
    }
    missing = {k: v for k, v in named_by_the_issue.items() if v not in captured | set(excluded)}
    assert not missing, f"silently dropped: {missing}"


def test_the_manifest_names_every_exclusion_and_every_class_left_out(fake_gh, snap):
    fake_gh.script(World.seeded().answers())
    manifest = snapshot(snap).capture(classes=["tag"])
    listed = [(e["class"], e["reason"]) for e in manifest["excluded"]]
    assert listed[: len(EXCLUDED)] == list(EXCLUDED)
    left_out = listed[len(EXCLUDED) :]
    assert [name for name, _ in left_out] == [n for n in NAMES if n != "tag"]
    assert all("not selected" in reason for _, reason in left_out)
    assert set(manifest["classes"]) == set(NAMES)


def test_exclusions_are_a_parameter_not_a_constant(fake_gh, snap):
    fake_gh.script(World.seeded().answers())
    reader = GithubForgeReader(GhTransport(), REPO)
    store = JsonlSnapshotStore(snap, forge="github", repository=REPO)
    extra = (("discussion", "Read by another tool."),)
    manifest = ForgeSnapshot(reader, store, clock=Ticks(), excluded=extra).capture(classes=["tag"])
    assert manifest["excluded"][0] == {"class": "discussion", "reason": "Read by another tool."}


# -- seams ---------------------------------------------------------------------------------


def test_each_class_honours_its_declared_seam(tmp_path):
    reader = GithubForgeReader(GhTransport(), REPO)
    store = JsonlSnapshotStore(tmp_path, forge="github", repository=REPO)
    assert isinstance(reader, ForgeReaderInterface)
    assert isinstance(store, SnapshotStoreInterface)
    assert isinstance(ForgeSnapshot(reader, store), ForgeSnapshotInterface)
    assert store.chain("label") == ChainHead(0, None)
    assert store.path("label") == tmp_path / "label.jsonl"


class ScriptedReader:
    """A reader that is not GitHub: the snapshot drives any forge through the seam."""

    forge = "forgejo"
    repository = REPO

    def read(self, forge_class: str, since: str | None) -> ForgeRead:
        spec = ForgeClass.named(forge_class)
        payload: Mapping[str, Any] = {"id": 1, "seen": since}
        return ForgeRead(spec.name, spec.native_class, (("1", payload),), None)


def test_the_snapshot_depends_on_the_reader_seam_not_on_github(tmp_path):
    store = JsonlSnapshotStore(tmp_path, forge="forgejo", repository=REPO)
    manifest = ForgeSnapshot(ScriptedReader(), store).capture(classes=["label"])
    assert manifest["forge"] == "forgejo" and manifest["classes"]["label"]["appended"] == 1
    record = lines(tmp_path / "label.jsonl")[0]
    assert record["forge"] == "forgejo" and record["captured_at"].endswith("Z")


# -- the command ---------------------------------------------------------------------------


def test_the_command_captures_reports_and_exits_zero(fake_gh, snap, capsys):
    fake_gh.script(World.seeded().answers())
    out = snap / "snap"
    assert main(["forge-snapshot", "--out", str(out), "--repo", REPO]) == 0
    printed = capsys.readouterr()
    assert f"vibey-gh forge-snapshot: github {REPO} into {out}" in printed.out
    assert "  issue: 2 observed, 2 appended, 0 unchanged; 2 record(s), head " in printed.out
    assert "  milestone: 1 observed" in printed.out
    assert f"{len(EXCLUDED)} artifact class(es) not captured" in printed.out
    assert "resume with --since 20" in printed.out and "(or --since resume)" in printed.out
    assert printed.err == ""


def test_the_command_exits_one_and_names_what_it_could_not_look_at(fake_gh, snap, capsys):
    world = World.seeded()
    world.milestones = []
    answers = world.answers()
    answers[World.listing(world.path("label"))] = {"err": "HTTP 401: Bad credentials\n", "code": 1}
    fake_gh.script(answers)
    code = main(
        [
            "forge-snapshot",
            "--out",
            str(snap),
            "--repo",
            REPO,
            "--classes",
            "label, milestone ,tag",
            "--since",
            "resume",
        ]
    )
    printed = capsys.readouterr()
    assert code == 1
    assert (
        "  label: COULD NOT LOOK, nothing written: `gh api repos/acme/widgets/labels" in printed.err
    )
    assert "  milestone: 0 observed, 0 appended, 0 unchanged; 0 record(s), head none" in printed.out
    assert "  issue: not selected" in printed.out
    assert "no resume point was recorded, so this capture is a full one" in printed.out
    assert "resume with" not in printed.out


def test_the_command_reads_the_repository_the_way_every_other_command_does(
    fake_gh, snap, monkeypatch, capsys
):
    fake_gh.script(World.seeded().answers())
    monkeypatch.setenv("GH_REPO", REPO)
    assert main(["forge-snapshot", "--out", str(snap), "--classes", "tag"]) == 0
    assert f"github {REPO} into" in capsys.readouterr().out

    monkeypatch.delenv("GH_REPO")
    fake_gh.script({"repo view --json nameWithOwner": {"err": "not a git repository\n", "code": 1}})
    assert main(["forge-snapshot", "--out", str(snap), "--classes", "tag"]) == 1
    assert "could not tell which repository to read: gh repo view" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--classes", "pr"], "unknown artifact class 'pr'"),
        (["--classes", " , "], "no artifact class selected"),
        (["--since", "tomorrow-ish"], "not an ISO 8601 moment"),
        (["--per-page", "500"], "per_page must be between 1 and 100"),
        (["--clock-skew", "-5"], "clock_skew must not be negative"),
    ],
)
def test_the_command_exits_two_for_arguments_that_name_no_capture(
    fake_gh, snap, capsys, argv, message
):
    code = main(["forge-snapshot", "--out", str(snap), "--repo", REPO, *argv])
    assert code == 2 and message in capsys.readouterr().err
    assert fake_gh.calls() == []


def test_the_command_exits_one_on_a_snapshot_it_cannot_extend(fake_gh, snap, capsys):
    snap.mkdir()
    (snap / MANIFEST_NAME).write_text("{", encoding="utf-8")
    assert main(["forge-snapshot", "--out", str(snap), "--repo", REPO]) == 1
    assert "manifest.json is not JSON" in capsys.readouterr().err
    assert fake_gh.calls() == []


def test_the_repository_read_is_the_shared_one(monkeypatch):
    # The command resolves `owner/name` through `github_state.repository`, the one resolver
    # every other command uses, rather than growing an eighth.
    monkeypatch.setenv("GH_REPO", "someone/else")
    assert github_state.repository() == "someone/else"


def test_the_schema_document_names_every_class_and_every_exclusion():
    """`docs/forge-snapshot.md` is the reference a reader has; it may not drift from the code."""
    text = (Path(__file__).resolve().parent.parent / "docs" / "forge-snapshot.md").read_text(
        encoding="utf-8"
    )
    for spec in CLASSES:
        assert f"| `{spec.name}.jsonl` | `{spec.name}` | `{spec.native_class}` |" in text
    for name, _reason in EXCLUDED:
        assert f"| `{name}` |" in text, f"docs/forge-snapshot.md does not name `{name}`"
    for schema in (RECORD_SCHEMA, MANIFEST_SCHEMA):
        assert f"`{schema}`" in text
