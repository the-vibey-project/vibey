# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh announce`: the concise changelog a docs deploy posts to Discord.

Nothing here leaves the machine. The forge is a scripted transport, the webhook a stub HTTP
server on 127.0.0.1, and the real webhook is never named: a URL that looks like one would
also trip vibey's tests/meta/test_webhooks_stay_out_of_the_tree.py.
"""

from __future__ import annotations

import dataclasses
import http.server
import json
import random
import re
import threading
import unicodedata
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Self

import pytest
import yaml

from vibey_gh import cli
from vibey_gh.announce import (
    ANNOUNCED_STEP,
    RUN_TITLE,
    Announcement,
    Announcer,
    AnnounceRequest,
    Change,
    ChangelogComposer,
    ChangeSet,
    CommitRange,
    CommitRecord,
    DiscordWebhook,
    Position,
    ReleaseHistory,
    Surface,
)
from vibey_gh.announce_records import KNOWN, REANCHORED, UNKNOWN
from vibey_gh.config import AnnounceConfig, GhConfig, GithubReleaseConfig, load_config
from vibey_gh.install import TEMPLATES, render_workflow
from vibey_gh.interfaces.announce_interface import (
    AnnouncerInterface,
    ChangelogComposerInterface,
    ReleaseHistoryInterface,
    WebhookPosterInterface,
)

GOLDEN = Path(__file__).resolve().parent / "golden"
WORKFLOW = TEMPLATES.parent / "workflows" / "release-surfaces.yml"
REPO = "octo/widgets"
HEAD = "c" * 40
BASE = "b" * 40
SERVER = "https://github.example"


def _commit(message: str, sha: str = "a" * 40) -> CommitRecord:
    return CommitRecord(sha, message)


def _composer(**overrides: Any) -> ChangelogComposer:
    return ChangelogComposer(AnnounceConfig(**overrides), REPO, SERVER)


def _request(tmp_path: Path, **overrides: Any) -> AnnounceRequest:
    values: dict[str, Any] = {
        "channel": "develop",
        "branch": "develop",
        "sha": HEAD,
        "repository": REPO,
        "server_url": SERVER,
        "site_dir": tmp_path / "site",
    }
    values.update(overrides)
    return AnnounceRequest(**values)


def _units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


FIRST_EVER = Position(None, "no earlier announcement is recorded", structural=True)


class ScriptedHistory:
    """A `ReleaseHistoryInterface` that answers from a script and records what it was asked."""

    def __init__(
        self,
        position: Position = FIRST_EVER,
        ranges: dict[tuple[str, str], tuple[CommitRange | None, str]] | None = None,
        commits: dict[str, CommitRecord] | None = None,
    ) -> None:
        self.position = position
        self.ranges = ranges or {}
        self.commits = commits or {}
        self.asked: list[tuple[str, ...]] = []

    def previous_position(self, branch: str, head: str) -> Position:
        self.asked.append(("position", branch, head))
        return self.position

    def compare(self, base: str, head: str) -> tuple[CommitRange | None, str]:
        self.asked.append(("compare", base, head))
        return self.ranges.get((base, head), (None, f"no range {base}...{head}"))

    def commit(self, sha: str) -> tuple[CommitRecord | None, str]:
        self.asked.append(("commit", sha))
        record = self.commits.get(sha)
        return (record, "") if record else (None, "no such commit")


class RecordingPoster:
    """A `WebhookPosterInterface` that answers as scripted and keeps what it was sent."""

    def __init__(self, answer: tuple[bool, str] = (True, "HTTP 204")) -> None:
        self.answer = answer
        self.sent: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, payload: Any) -> tuple[bool, str]:
        self.sent.append((url, dict(payload)))
        return self.answer


class ScriptedTransport:
    """The slice of `GhTransportInterface` `ReleaseHistory` uses: `survey`, from a table."""

    def __init__(self, answers: dict[str, tuple[Any, str]]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def survey(self, args: Sequence[str], **_: Any) -> tuple[Any, str]:
        assert args[0] == "api"
        path = args[1]
        self.asked.append(path)
        return self.answers.get(path, ([], f"`gh api` failed: 404 {path}"))


# ---------------------------------------------------------------------------------------
# The seams are the declared interfaces.


def test_every_class_implements_its_interface(tmp_path):
    history = ReleaseHistory(REPO, "1", transport=ScriptedTransport({}))
    assert isinstance(history, ReleaseHistoryInterface)
    assert isinstance(_composer(), ChangelogComposerInterface)
    assert isinstance(DiscordWebhook(), WebhookPosterInterface)
    assert isinstance(Announcer(GhConfig(root=tmp_path), history), AnnouncerInterface)
    # The production history defaults to the real transport.
    assert ReleaseHistory(REPO, "1")._transport is not None


# ---------------------------------------------------------------------------------------
# Grouping, order, the cap, and the limit.

_RANGE = [
    "feat(gh): announce a concise changelog (#101)",
    "fix(paper): draw the release cadence from tags (#102)",
    "docs(canon): ratify sub-doctrine 12.f (#103)",
    "chore(merge): bring develop forward",
    "Merge pull request #7 from octo/topic",
    "feat(api)!: drop the v1 endpoints (#104)",
    "fix(db): keep the lock\n\nBREAKING CHANGE: the lock key changed (#105)",
    "perf(queue): claim in one round trip",
]


def test_changes_are_grouped_breaking_first_and_noise_is_counted():
    changes = _composer().from_commits([_commit(m) for m in _RANGE])
    groups = [change.group for change in changes.changes]
    assert groups == ["Breaking", "Breaking", "Added", "Fixed", "Other", "Other"]
    assert changes.noise == 2
    # Newest first within a group: the range is oldest first.
    assert [c.description for c in changes.changes[:2]] == [
        "keep the lock",
        "drop the v1 endpoints",
    ]
    breaking = changes.changes[1]
    assert (breaking.word, breaking.scope, breaking.reference) == ("Feature", "api", "#104")
    perf = changes.changes[4]
    assert (perf.word, perf.reference, perf.url) == (
        "Performance",
        "aaaaaaa",
        f"{SERVER}/{REPO}/commit/{'a' * 40}",
    )


def test_a_rendered_message_reads_as_grouped_lines():
    message = _composer().render("head:", _composer().from_commits([_commit(m) for m in _RANGE]))
    lines = message.content.splitlines()
    assert lines[0] == "head:"
    assert lines.index("**Breaking**") < lines.index("**Added**") < lines.index("**Fixed**")
    assert lines.index("**Fixed**") < lines.index("**Other**")
    assert (
        f"- Feature · gh: announce a concise changelog ([#101](<{SERVER}/{REPO}/pull/101>))"
        in lines
    )
    assert lines[-1] == "+2 maintenance commits"
    assert message.listed == 6


def test_the_cap_lists_max_changes_and_counts_the_rest():
    commits = [_commit(f"feat: change number {n} (#{n})") for n in range(20)]
    message = _composer().render("head:", _composer().from_commits(commits), more_url="https://x")
    assert sum(line.startswith("- ") for line in message.content.splitlines()) == 8
    assert "…and 12 more · [full list](<https://x>)" in message.content


def test_a_breaking_change_is_never_capped():
    commits = [_commit(f"feat!: break {n}") for n in range(3)]
    commits += [_commit(f"fix: repair {n}") for n in range(10)]
    message = _composer(max_changes=1).render("h", _composer().from_commits(commits))
    assert message.content.count("break ") == 3
    assert "…and 9 more" in message.content


@pytest.mark.parametrize("count", [1, 30, 400])
def test_the_message_never_exceeds_discords_limit(count):
    """Long subjects, many of them, and emoji (two UTF-16 units each) still fit."""
    subject = "feat(scope): " + "😀 long words here " * 60
    commits = [_commit(f"{subject}{n} (#{n})") for n in range(count)]
    composer = _composer(max_subject_chars=400, max_changes=50)
    surfaces = [Surface(f"surface {n}", f"https://example.test/{n}") for n in range(6)]
    message = composer.render("head:", composer.from_commits(commits), surfaces=surfaces)
    assert _units(message.content) <= 2000
    listed = sum(line.startswith("- ") for line in message.content.splitlines())
    assert listed == message.listed
    if count > listed:
        assert f"…and {count - listed} more" in message.content


def test_breaking_changes_that_overflow_are_shortened_then_counted_by_name():
    subject = "feat(core)!: " + "x" * 390
    commits = [_commit(f"{subject} {n}") for n in range(100)]
    composer = _composer(max_subject_chars=400)
    message = composer.render("head:", composer.from_commits(commits))
    assert _units(message.content) <= 2000
    listed = message.listed
    assert 0 < listed < 100
    assert f"**+{100 - listed} more breaking changes**" in message.content
    # Shortened to the floor before any was dropped.
    first = message.content.splitlines()[2].split(" ([")[0]
    assert first.endswith("…") and len(first) < 70


def test_one_breaking_change_that_overflows_is_counted_in_the_singular():
    composer = _composer(max_message_chars=200, max_subject_chars=100)
    changes = composer.from_commits([_commit("feat!: " + "y" * 90)])
    message = composer.render("h" * 150, changes)
    assert "**+1 more breaking change**" in message.content
    assert _units(message.content) <= 200


def test_a_long_subject_is_cut_with_an_ellipsis():
    composer = _composer(max_subject_chars=20)
    line = composer.render("h", composer.from_commits([_commit("fix: " + "abcde " * 10)]))
    assert "- Fix: abcde abcde abcde a…" in line.content


def test_the_surface_line_goes_before_the_message_is_cut():
    composer = _composer(max_message_chars=200)
    message = composer.render("h" * 190, ChangeSet(), surfaces=[Surface("site", "https://s")])
    assert message.content == "h" * 190


def test_a_header_too_long_for_any_message_is_cut_hard():
    composer = _composer(max_message_chars=200)
    message = composer.render("h" * 500, ChangeSet())
    assert _units(message.content) == 200
    assert message.content.endswith("…")


def test_other_can_be_counted_instead_of_listed():
    composer = _composer(include_other=False)
    message = composer.render("h", composer.from_commits([_commit(m) for m in _RANGE]))
    assert "**Other**" not in message.content
    assert "…and 2 more" in message.content


def test_groups_and_words_are_configuration():
    cfg = AnnounceConfig.from_table(
        {
            "groups": {"New": ["feat", "perf"], "Docs": ["docs"]},
            "type_words": {"perf": "Speed"},
            "breaking_group": "Heads up",
            "other_group": "Misc",
        }
    )
    composer = ChangelogComposer(cfg, REPO, SERVER)
    message = composer.render("h", composer.from_commits([_commit(m) for m in _RANGE]))
    lines = message.content.splitlines()
    assert lines.index("**Heads up**") < lines.index("**New**") < lines.index("**Docs**")
    assert lines.index("**Docs**") < lines.index("**Misc**")
    assert any(line.startswith("- Speed · queue:") for line in lines)


def test_links_can_be_switched_off():
    composer = _composer(link_pull_requests=False, link_compare=False, link_surfaces=False)
    message = composer.render(
        "h",
        composer.from_commits([_commit("feat: a (#9)")]),
        more_url="https://compare",
        surfaces=[Surface("site", "https://s")],
    )
    assert message.content == "h\n**Added**\n- Feature: a (#9)"


def test_a_subject_that_is_not_conventional_is_listed_as_it_is():
    composer = _composer()
    changes = composer.from_commits([_commit("Update the thing (#4)"), _commit("Tidy: x")])
    assert [(c.group, c.word) for c in changes.changes] == [("Other", ""), ("Other", "")]
    message = composer.render("h", changes)
    assert f"- Update the thing ([#4](<{SERVER}/{REPO}/pull/4>))" in message.content
    # A change carrying no reference at all renders bare.
    bare = Change("Other", "", "", "nothing to link")
    assert composer.render("h", ChangeSet((bare,))).content.endswith("- nothing to link")


def test_unread_commits_are_counted_not_lost():
    message = _composer().render("h", ChangeSet(unread=3))
    assert message.content == "h\n…and 3 more"


# ---------------------------------------------------------------------------------------
# Commit subjects are data.

_HOSTILE = (
    "feat(x): @everyone @here <@123> <@!45> <@&678> <#9> </cmd:1> <:e:2> <t:3> "
    "[click](https://evil.example) https://evil.example/a `rm -rf` **bold** ||spoil|| "
    "# heading > quote ~~gone~~ _it_ :smile: \\ " + chr(0x202E) + "gnirts" + chr(0x200B) + " end"
)


def test_mentions_links_and_markdown_in_a_subject_are_neutralised():
    composer = _composer(max_subject_chars=400)
    content = composer.render("h", composer.from_commits([_commit(_HOSTILE)])).content
    line = next(line for line in content.splitlines() if line.startswith("- "))
    line = line.rsplit(" ([", 1)[0]  # the commit link is ours, not the subject's
    for dangerous in ("@everyone", "@here", "<@", "<#", "</", "<:", "<t", "[click", "`rm"):
        assert not re.search(r"(?<!\\)" + re.escape(dangerous), line), dangerous
    assert "https://" not in line and "https\\://evil" in line
    for marker in ("**", "||", "~~", "_it_", ":smile:"):
        assert marker not in line, marker
    assert chr(0x202E) not in line and chr(0x200B) not in line
    assert "\\\\" in line  # a backslash in the subject is itself escaped


def test_the_payload_can_ping_nobody(tmp_path):
    history = ScriptedHistory(commits={HEAD: _commit(_HOSTILE, HEAD)})
    poster = RecordingPoster()
    Announcer(GhConfig(root=tmp_path), history, poster=poster, out=lambda _: None).run(
        _request(tmp_path), "https://hooks.example/abc"
    )
    ((_url, payload),) = poster.sent
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["flags"] == 4
    assert payload["username"] == "vibey"
    assert _units(payload["content"]) <= 2000


def test_embeds_can_be_left_to_discord(tmp_path):
    cfg = GhConfig(root=tmp_path, announce=AnnounceConfig(suppress_embeds=False, username="bot"))
    payload = Announcer(cfg, ScriptedHistory()).payload(Announcement("x"))
    assert "flags" not in payload and payload["username"] == "bot"


# ---------------------------------------------------------------------------------------
# A release announces its own notes.

_CHANGELOG = """# Changelog

## [Unreleased]

### Features

* **gh:** not released yet

## [2.1.0](https://example/compare) (2026-09-24)

### BREAKING CHANGES

* **packaging:** one distribution, one version. Everything else
  follows from that.

### Features

* **gh:** announce a concise changelog to Discord
  ([#1106](https://example/pull/1106)). And more.
* **paper:** draw the cadence from the tags (#1104)

### Bug Fixes

- **db:** keep the lock; no more races

### Security

* plain entry with a [link](https://x.example) in it

stray paragraph that is not an entry

## [2.0.0] (2026-09-21)

### Added

* **old:** not this release
"""


def test_a_version_section_becomes_grouped_changes():
    notes = _composer().from_changelog(_CHANGELOG, "2.1.0")
    assert notes is not None
    assert notes.previous_version == "2.0.0"
    got = [(c.group, c.word, c.scope, c.description, c.reference) for c in notes.changes.changes]
    assert got == [
        ("Breaking", "", "packaging", "one distribution, one version", ""),
        ("Added", "Feature", "gh", "announce a concise changelog to Discord", "#1106"),
        ("Added", "Feature", "paper", "draw the cadence from the tags", "#1104"),
        ("Fixed", "Fix", "db", "keep the lock; no more races", ""),
        ("Other", "Security", "", "plain entry with a link in it", ""),
    ]


def test_the_newest_section_names_no_previous_and_a_missing_one_is_none():
    assert _composer().from_changelog(_CHANGELOG, "2.0.0").previous_version is None
    unreleased_next = "## [9.9.9]\n\n* x\n\n## [Unreleased]\n"
    assert _composer().from_changelog(unreleased_next, "9.9.9").previous_version is None
    assert _composer().from_changelog(_CHANGELOG, "7.7.7") is None


# ---------------------------------------------------------------------------------------
# Where the last announcement stopped: a position, from the Actions API.


def _runs(*runs: dict[str, Any]) -> dict[str, Any]:
    return {"workflow_runs": list(runs)}


def _title(branch: str, ref: str) -> str:
    return f"Release surfaces · {branch} · {ref}"


def _jobs(conclusion: str) -> dict[str, Any]:
    return {
        "jobs": [
            {"steps": None},
            {"steps": [{"name": "Other step", "conclusion": "success"}]},
            {"steps": [{"name": ANNOUNCED_STEP, "conclusion": conclusion}]},
        ]
    }


_API = f"repos/{REPO}"
_LIST = f"{_API}/actions/workflows/7/runs?status=success&per_page=100&page=1"


def _history(answers: dict[str, tuple[Any, str]], run_id: str = "99", pages: int = 10):
    base = {f"{_API}/actions/runs/99": ({"workflow_id": 7}, "")}
    transport = ScriptedTransport(base | answers)
    return ReleaseHistory(REPO, run_id, transport=transport, pages=pages), transport


def test_the_previous_position_is_the_last_accepted_run_for_the_branch():
    history, transport = _history(
        {
            _LIST: (
                _runs(
                    {"id": 1, "display_title": "Release surfaces"},  # before run titles
                    {"id": 2, "display_title": _title("main", "d" * 40)},
                    {"id": 3, "display_title": _title("develop", "e" * 40)},
                    {"id": 4, "display_title": _title("develop", BASE)},
                ),
                "",
            ),
            f"{_API}/actions/runs/3/jobs?per_page=100": (_jobs("skipped"), ""),
            f"{_API}/actions/runs/4/jobs?per_page=100": (_jobs("success"), ""),
        }
    )
    assert history.previous_position("develop", HEAD) == Position(BASE)
    # The branch filter is never trusted: a workflow_run run belongs to the default branch.
    assert all("branch=" not in path for path in transport.asked)


def test_a_dispatched_run_is_resolved_through_the_release_run_it_named():
    history, _ = _history(
        {
            _LIST: (_runs({"id": 5, "display_title": _title("develop", "12345")}), ""),
            f"{_API}/actions/runs/5/jobs?per_page=100": (_jobs("success"), ""),
            f"{_API}/actions/runs/12345": ({"head_sha": BASE}, ""),
        }
    )
    assert history.previous_position("develop", HEAD) == Position(BASE)


def test_a_dispatched_run_that_names_no_commit_is_unknown():
    history, _ = _history(
        {
            _LIST: (_runs({"id": 5, "display_title": _title("develop", "12345")}), ""),
            f"{_API}/actions/runs/5/jobs?per_page=100": (_jobs("success"), ""),
            f"{_API}/actions/runs/12345": ({"head_sha": "not-a-sha"}, ""),
        }
    )
    position = history.previous_position("develop", HEAD)
    assert position.sha is None and not position.structural
    assert "release run 12345 names no commit" in position.reason


def test_the_first_ever_run_finds_no_earlier_announcement():
    history, _ = _history({_LIST: (_runs(), "")})
    assert history.previous_position("develop", HEAD) == Position(
        None, "no earlier announcement is recorded for develop", structural=True
    )


def test_a_full_page_of_other_runs_reads_the_next_page_up_to_the_limit():
    other = [{"id": n, "display_title": _title("main", "d" * 40)} for n in range(100)]
    history, transport = _history({_LIST: (_runs(*other), "")}, pages=1)
    assert history.previous_position("develop", HEAD) == Position(
        None, "no accepted announcement for develop in the last 100 runs", structural=True
    )
    assert transport.asked.count(_LIST) == 1


@pytest.mark.parametrize(
    "answers, run_id, expected",
    [
        ({}, "", "this run's id is unknown"),
        ({f"{_API}/actions/runs/99": ([], "boom")}, "99", "did not name this workflow (boom)"),
        ({f"{_API}/actions/runs/99": ({}, "")}, "99", "did not name this workflow (no id)"),
        ({_LIST: ([], "down")}, "99", "did not list earlier runs (down)"),
        ({_LIST: ([], "")}, "99", "did not list earlier runs (malformed)"),
        (
            {
                _LIST: (_runs({"id": 3, "display_title": _title("develop", BASE)}), ""),
                f"{_API}/actions/runs/3/jobs?per_page=100": ([], "denied"),
            },
            "99",
            "did not list run 3's jobs (denied)",
        ),
        (
            {
                _LIST: (_runs({"id": 3, "display_title": _title("develop", BASE)}), ""),
                f"{_API}/actions/runs/3/jobs?per_page=100": ([], ""),
            },
            "99",
            "did not list run 3's jobs (malformed)",
        ),
    ],
)
def test_an_unreadable_history_is_unknown_and_says_why(answers, run_id, expected):
    """Every one of these is a source that could not be READ: never structural, so the
    announcement is `position=unknown` and the watermark does not move (10.g)."""
    history, _ = _history(answers, run_id=run_id)
    position = history.previous_position("develop", HEAD)
    assert position.sha is None and not position.structural
    assert expected in position.reason


def test_a_range_is_read_page_by_page_and_counts_what_it_could_not_read():
    first = [{"sha": f"{n:040x}", "commit": {"message": f"fix: {n}"}} for n in range(100)]
    second = [{"sha": "f" * 40, "commit": None}]
    path = f"{_API}/compare/{BASE}...{HEAD}?per_page=100&page="
    history, _ = _history(
        {
            f"{path}1": (
                {"status": "ahead", "total_commits": 150, "html_url": "u", "commits": first},
                "",
            ),
            f"{path}2": ({"commits": second}, ""),
            f"{path}3": ({"commits": []}, ""),
        }
    )
    found, why = history.compare(BASE, HEAD)
    assert why == "" and found is not None
    assert (found.status, found.total, len(found.commits), found.html_url) == (
        "ahead",
        150,
        101,
        "u",
    )
    assert found.commits[-1] == CommitRecord("f" * 40, "")


def test_a_range_stops_at_the_page_limit():
    path = f"{_API}/compare/{BASE}...{HEAD}?per_page=100&page=1"
    batch = [{"sha": "1" * 40, "commit": {"message": "x"}}] * 100
    history, _ = _history(
        {path: ({"status": "ahead", "total_commits": 900, "commits": batch}, "")}, pages=1
    )
    found, _ = history.compare(BASE, HEAD)
    assert found is not None and found.total - len(found.commits) == 800


def test_a_range_that_cannot_be_read_says_why():
    history, _ = _history({})
    assert history.compare("../x", HEAD)[1].endswith("is not a range of git references")
    found, why = history.compare(BASE, HEAD)
    assert found is None and why.startswith("the compare API did not answer")


def test_one_commit_is_read_or_said_to_be_unreadable():
    history, _ = _history({f"{_API}/commits/{HEAD}": ({"commit": {"message": "feat: x"}}, "")})
    assert history.commit(HEAD) == (CommitRecord(HEAD, "feat: x"), "")
    record, why = history.commit(BASE)
    assert record is None and "the commits API did not answer" in why


# ---------------------------------------------------------------------------------------
# What a deploy announces.


def _announce(tmp_path: Path, history: ScriptedHistory, **request: Any) -> str:
    announcer = Announcer(GhConfig(root=tmp_path), history)
    return announcer.compose(_request(tmp_path, **request)).content


def test_a_known_previous_position_announces_the_range_since_it(tmp_path):
    rng = CommitRange("ahead", 3, tuple(_commit(m) for m in _RANGE[:2]), "https://cmp")
    history = ScriptedHistory(position=Position(BASE), ranges={(BASE, HEAD): (rng, "")})
    content = _announce(tmp_path, history)
    assert content.startswith(f"**octo/widgets** published `develop` from `{HEAD[:12]}`")
    assert f"changes since `{BASE[:12]}`:" in content.splitlines()[0]
    assert "…and 1 more · [compare bbbbbbb…ccccccc](<https://cmp>)" in content


def test_the_first_announcement_re_anchors_and_says_so(tmp_path):
    history = ScriptedHistory(commits={HEAD: _commit("fix(x): mend (#8)", HEAD)})
    announcement = Announcer(GhConfig(root=tmp_path), history).compose(_request(tmp_path))
    content = announcement.content
    assert announcement.position == REANCHORED
    assert "re-anchored here (no earlier announcement is recorded) — this commit only:" in (content)
    assert "- Fix · x: mend" in content
    assert f"[this commit](<{SERVER}/{REPO}/commit/{HEAD}>)" in content
    assert ("compare", BASE, HEAD) not in history.asked


def test_an_unreadable_single_commit_is_still_counted(tmp_path):
    content = _announce(tmp_path, ScriptedHistory())
    assert "…and 1 more" in content


def test_an_unreadable_history_is_unknown_and_not_recorded(tmp_path):
    history = ScriptedHistory(
        position=Position(None, "HTTP 502 from the Actions API"),
        commits={HEAD: _commit("fix(x): mend (#8)", HEAD)},
    )
    announcement = Announcer(GhConfig(root=tmp_path), history).compose(_request(tmp_path))
    assert announcement.position == UNKNOWN
    assert announcement.content.splitlines()[0].endswith(
        "changes since: unknown (HTTP 502 from the Actions API) — this commit only; "
        "the next announcement covers the span again:"
    )


def test_a_commit_already_announced_is_a_duplicate(tmp_path):
    announcer = Announcer(GhConfig(root=tmp_path), ScriptedHistory(position=Position(HEAD)))
    announcement = announcer.compose(_request(tmp_path))
    assert announcement.duplicate and announcement.position == KNOWN
    assert announcement.content.splitlines()[0].endswith("· already announced")


@pytest.mark.parametrize(
    "answer, reason, position",
    [
        ((None, "the compare API did not answer"), "changes since: unknown (the compare", UNKNOWN),
        (
            (CommitRange("diverged", 0, (), ""), ""),
            (
                "re-anchored here (the last announced commit bbbbbbbbbbbb is not behind this one "
                "(diverged; history was rewritten))"
            ),
            REANCHORED,
        ),
    ],
)
def test_a_position_that_cannot_be_compared(tmp_path, answer, reason, position):
    """A compare that did not answer is unreadable: unknown, not recorded. One that answered
    `diverged` (a force-push under the last position) is structural: re-anchored, said."""
    history = ScriptedHistory(position=Position(BASE), ranges={(BASE, HEAD): answer})
    announcement = Announcer(GhConfig(root=tmp_path), history).compose(_request(tmp_path))
    assert reason in ComposerEscape.plain(announcement.content)
    assert announcement.position == position


def test_the_surfaces_this_deploy_produced_follow_the_changelog(tmp_path):
    site = tmp_path / "site"
    (site / "paper").mkdir(parents=True)
    (site / "paper" / "index.html").write_text("x")
    (site / "book.epub").write_text("x")
    content = _announce(tmp_path, ScriptedHistory(position=Position(HEAD)))
    root = "https://octo.github.io/widgets/develop/"
    assert content.splitlines()[-1] == (
        f"Read: [site](<{root}>) · [paper HTML](<{root}paper/>) · [book EPUB](<{root}book.epub>)"
    )


def _release_repo(tmp_path: Path, changelog: str | None = _CHANGELOG, version: str = "2.1.0"):
    (tmp_path / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n')
    if changelog is not None:
        (tmp_path / "CHANGELOG.md").write_text(changelog)
    return GhConfig(root=tmp_path, version_files=("pyproject.toml",))


def _release(tmp_path: Path, cfg: GhConfig, history: ScriptedHistory, **request: Any) -> str:
    values = {"channel": "main", "branch": "main"} | request
    return Announcer(cfg, history).compose(_request(tmp_path, **values)).content


def test_a_release_announces_its_own_notes_and_the_tag_range(tmp_path):
    cfg = _release_repo(tmp_path)
    rng = CommitRange("ahead", 12, (), "https://cmp")
    history = ScriptedHistory(ranges={("v2.0.0", HEAD): (rng, "")})
    content = _release(tmp_path, cfg, history)
    first = content.splitlines()[0]
    assert first == (
        f"**octo/widgets** released **2.1.0** on `main` from `{HEAD[:12]}` · release notes, "
        "12 commits since `v2.0.0`:"
    )
    assert "**Breaking**\n- packaging: one distribution, one version" in content
    assert "[compare v2.0.0…ccccccc](<https://cmp>)" in content
    assert ("position", "main", HEAD) not in history.asked


@pytest.mark.parametrize(
    "answer, reason",
    [
        ((None, "tag missing"), "tag range unavailable (tag missing):"),
        (
            (CommitRange("behind", 0, (), ""), ""),
            "tag range unavailable (v2.0.0 is not behind this commit (behind)):",
        ),
    ],
)
def test_a_release_without_its_tag_range_still_posts_its_notes(tmp_path, answer, reason):
    cfg = _release_repo(tmp_path)
    content = _release(tmp_path, cfg, ScriptedHistory(ranges={("v2.0.0", HEAD): answer}))
    assert ComposerEscape.plain(content.splitlines()[0]).endswith(reason)
    assert f"[full changelog](<{SERVER}/{REPO}/blob/{HEAD}/CHANGELOG.md>)" in content


def test_the_first_release_has_no_tag_range_to_read(tmp_path):
    cfg = _release_repo(tmp_path, version="2.0.0")
    history = ScriptedHistory()
    content = _release(tmp_path, cfg, history)
    assert "tag range unavailable (no earlier version in CHANGELOG.md)" in ComposerEscape.plain(
        content
    )
    assert not [asked for asked in history.asked if asked[0] == "compare"]


def test_a_release_with_no_changelog_section_is_unknown_and_this_commit_only(tmp_path):
    cfg = _release_repo(tmp_path, changelog=None)
    history = ScriptedHistory(commits={HEAD: _commit("chore(release): 2.1.0", HEAD)})
    content = _release(tmp_path, cfg, history)
    assert "re-anchored here (no CHANGELOG.md section for 2.1.0)" in ComposerEscape.plain(content)
    assert "+1 maintenance commit" in content


def test_a_release_whose_version_cannot_be_read_says_so(tmp_path):
    content = _release(tmp_path, GhConfig(root=tmp_path), ScriptedHistory())
    assert "released a release on `main`" in content
    assert "no CHANGELOG.md section for this version" in ComposerEscape.plain(content)


def test_a_version_given_on_the_command_line_wins(tmp_path):
    cfg = _release_repo(tmp_path, version="0.0.1")
    content = _release(tmp_path, cfg, ScriptedHistory(), version="2.1.0")
    assert "released **2.1.0**" in content


class ComposerEscape:
    """Reads escaped Discord text back as plain text, for assertions about wording."""

    @staticmethod
    def plain(text: str) -> str:
        return re.sub(r"\\(.)", r"\1", text)


# ---------------------------------------------------------------------------------------
# Posting: said out loud, never fatal, never the URL.

_HOOK = "http://127.0.0.1:9/hooks/secret-token-value"


def _run(tmp_path, **kwargs: Any) -> tuple[list[str], RecordingPoster, int, str]:
    out: list[str] = []
    poster = kwargs.pop("poster", RecordingPoster())
    cfg = kwargs.pop("cfg", GhConfig(root=tmp_path))
    output = tmp_path / "github_output"
    history = ScriptedHistory(commits={HEAD: _commit("feat: x (#1)", HEAD)})
    code = Announcer(cfg, history, poster=poster, out=out.append).run(
        _request(tmp_path), kwargs.pop("url", _HOOK), github_output=str(output), **kwargs
    )
    return out, poster, code, output.read_text() if output.exists() else ""


def test_no_secret_is_said_and_passes(tmp_path):
    out, poster, code, output = _run(tmp_path, url="")
    assert out == ["announce: no DISCORD_WEBHOOK_URL secret is set; nothing posted"]
    assert (code, poster.sent, output) == (0, [], "posted=false\nposition=unknown\n")


def test_switched_off_is_said_and_passes(tmp_path):
    cfg = GhConfig(root=tmp_path, announce=AnnounceConfig(enabled=False))
    out, poster, code, _ = _run(tmp_path, cfg=cfg)
    assert out == ["announce: [announce] enabled = false; nothing posted"]
    assert (code, poster.sent) == (0, [])


def test_a_dry_run_prints_the_message_and_posts_nothing(tmp_path):
    out, poster, code, output = _run(tmp_path, url="", dry_run=True)
    assert out[0].startswith("**octo/widgets** published") and poster.sent == []
    assert (code, output) == (0, "posted=false\nposition=reanchored\n")


def test_an_accepted_post_is_reported_and_recorded(tmp_path):
    out, poster, code, output = _run(tmp_path)
    assert out == [
        "announce: posted 1 change and 1 surface link to Discord (HTTP 204); position reanchored",
    ]
    assert (code, output) == (0, "posted=true\nposition=reanchored\n")
    assert poster.sent[0][0] == _HOOK


def test_a_failed_post_is_a_warning_and_never_names_the_webhook(tmp_path):
    poster = RecordingPoster((False, f"URLError: refused by {_HOOK}"))
    out, _, code, output = _run(tmp_path, poster=poster)
    assert code == 0 and output == "posted=false\nposition=reanchored\n"
    assert out == [
        (
            "::warning::announce: the Discord webhook post failed and the deploy stands: "
            "URLError: refused by <webhook>"
        )
    ]


def test_without_a_github_output_nothing_is_written(tmp_path):
    out: list[str] = []
    Announcer(GhConfig(root=tmp_path), ScriptedHistory(), out=out.append).run(
        _request(tmp_path), ""
    )
    assert not (tmp_path / "github_output").exists()


class StubWebhook:
    """A local HTTP server standing in for Discord: records bodies, answers with `status`."""

    def __init__(self, status: int) -> None:
        received: list[dict[str, Any]] = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers["Content-Length"])
                received.append(json.loads(self.rfile.read(length)))
                self.send_response(status)
                self.end_headers()

            def log_message(self, *_: Any) -> None:
                return None

        self.received = received
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/hook/secret-token"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def stub() -> Iterator[type[StubWebhook]]:
    yield StubWebhook


def test_the_webhook_receives_the_payload(stub):
    with stub(204) as server:
        ok, detail = DiscordWebhook(timeout=5).post(server.url, {"content": "hi"})
    assert (ok, detail) == (True, "HTTP 204")
    assert server.received == [{"content": "hi"}]


def test_a_webhook_error_is_reported_without_the_url(stub):
    with stub(500) as server:
        ok, detail = DiscordWebhook(timeout=5).post(server.url, {"content": "hi"})
    assert (ok, detail) == (False, "HTTP 500")


def test_an_unreachable_or_malformed_webhook_is_redacted():
    closed = "http://127.0.0.1:1/api/hook/secret-token"
    ok, detail = DiscordWebhook(timeout=5).post(closed, {})
    assert not ok and "secret-token" not in detail and "127.0.0.1:1" not in detail
    malformed = "http://[bad-host/api/hook/secret-token"
    ok, detail = DiscordWebhook(timeout=5).post(malformed, {})
    assert not ok and detail.startswith("ValueError") and "secret-token" not in detail
    assert DiscordWebhook().post("file:///etc/passwd", {}) == (
        False,
        "the webhook is not an http(s) URL",
    )
    assert DiscordWebhook.redact("see https://x.example/y and more", "") == "see <url> and more"


def test_the_command_posts_through_the_cli(tmp_path, monkeypatch, capsys, stub):
    """End to end through `vibey-gh announce`, on the release path, which asks the forge for
    nothing when the changelog names no earlier version: no network, only the stub."""
    (tmp_path / ".vibey-gh.toml").write_text('[version]\nfiles = ["pyproject.toml"]\n')
    _release_repo(tmp_path, version="2.0.0")
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    args = ["announce", "--channel", "main", "--branch", "main", "--sha", HEAD]
    args += ["--repository", REPO, "--run-id", "", "--site-dir", str(tmp_path)]
    with stub(204) as server:
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", server.url)
        assert cli.main(args) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("announce: posted 1 change") and server.url not in printed
    assert "old: not this release" in ComposerEscape.plain(server.received[0]["content"])
    assert output.read_text() == "posted=true\nposition=known\n"


def test_the_command_passes_with_no_secret(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    args = ["announce", "--channel", "develop", "--branch", "develop", "--sha", HEAD]
    assert cli.main([*args, "--repository", REPO]) == 0
    assert "nothing posted" in capsys.readouterr().out


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("sha", "HEAD", "--sha must be a hex commit id"),
        ("repository", "no-slash", "--repository must be owner/name"),
        ("repository", "a/b/c", "--repository must be owner/name"),
        ("channel", "../x", "--channel is not a plain name"),
        ("branch", "a b", "--branch is not a git branch name"),
        ("branch", "release/../x", "--branch is not a git branch name"),
        ("branch", "-x", "--branch is not a git branch name"),
        ("branch", "a.lock", "--branch is not a git branch name"),
        ("branch", "a/.b", "--branch is not a git branch name"),
        ("branch", "a.lock/b", "--branch is not a git branch name"),
        ("branch", "@", "--branch is not a git branch name"),
        ("branch", "", "--branch is not a git branch name"),
    ],
)
def test_a_request_refuses_anything_that_is_not_a_plain_name(tmp_path, field, value, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        _request(tmp_path, **{field: value})


# ---------------------------------------------------------------------------------------
# The golden message: the format, reviewed as text.


def test_the_golden_announcement(tmp_path):
    """test/golden/announce-develop.txt is what a develop deploy posts for this range. A
    change to the format changes that file, so the format is reviewed as text in the diff."""
    messages = [
        "feat(gh): announce a concise changelog with every docs deploy (#1106)",
        "fix(paper): draw the release cadence from the tags the repository holds (#1104)",
        "chore(merge): bring develop forward",
        "docs(canon): ratify sub-doctrine 12.f, unattended approval (#1103)",
        "feat(storm)!: lanes run one at a time (#1102)",
        "fix(gh): quote the paper's author fields for the shell (#1101)",
        "Merge pull request #1100 from the-vibey-project/develop",
        "perf(queue): claim a job in one round trip (#1099)",
    ]
    rng = CommitRange(
        "ahead",
        len(messages),
        tuple(_commit(m, f"{n:040x}") for n, m in enumerate(reversed(messages))),
        "https://github.com/the-vibey-project/vibey/compare/b16ba7b590ab...600f3db2883d",
    )
    base, head = "b16ba7b590ab" + "0" * 28, "600f3db2883d" + "0" * 28
    site = tmp_path / "site"
    (site / "paper").mkdir(parents=True)
    for name in ("paper.pdf", "paper/index.html", "book.pdf", "book.epub", "book-print.html"):
        (site / name).write_text("x")
    request = AnnounceRequest(
        channel="develop",
        branch="develop",
        sha=head,
        repository="the-vibey-project/vibey",
        site_dir=site,
    )
    history = ScriptedHistory(position=Position(base), ranges={(base, head): (rng, "")})
    content = Announcer(GhConfig(root=tmp_path), history).compose(request).content
    golden = (GOLDEN / "announce-develop.txt").read_text(encoding="utf-8")
    assert content == golden.rstrip("\n")
    assert _units(content) <= 2000


# ---------------------------------------------------------------------------------------
# The workflow and the module agree.


def _rendered_workflow(tmp_path: Path) -> dict[str, Any]:
    return yaml.safe_load(render_workflow(WORKFLOW, GhConfig(root=tmp_path)))


def test_the_run_name_records_what_the_history_reads_back(tmp_path):
    """The template's `run-name` and `RUN_TITLE` are one format written in two places; a
    change to either without the other would make every announcement `unknown`."""
    run_name = _rendered_workflow(tmp_path)["run-name"]
    branch_expr = "${{ github.event.workflow_run.head_branch || inputs.branch }}"
    ref_expr = "${{ github.event.workflow_run.head_sha || inputs.run_id }}"
    assert branch_expr in run_name and ref_expr in run_name
    for ref in (BASE, "35999517673"):
        title = run_name.replace(branch_expr, "develop").replace(ref_expr, ref)
        match = RUN_TITLE.search(title)
        assert match is not None and (match["branch"], match["ref"]) == ("develop", ref)


def test_the_position_marker_runs_only_when_the_post_was_accepted(tmp_path):
    steps = _rendered_workflow(tmp_path)["jobs"]["docs"]["steps"]
    names = [step.get("name") for step in steps]
    announce = steps[names.index("Announce the published surfaces")]
    marker = steps[names.index(ANNOUNCED_STEP)]
    assert names.index(ANNOUNCED_STEP) == names.index("Announce the published surfaces") + 1
    assert announce["id"] == "announce"
    assert marker["if"] == (
        "steps.announce.outputs.posted == 'true' && steps.announce.outputs.position != 'unknown'"
    )
    assert "printf 'posted=false\\nposition=unknown\\n' >> \"$GITHUB_OUTPUT\"" in announce["run"]
    docs = _rendered_workflow(tmp_path)["jobs"]["docs"]
    assert docs["permissions"]["actions"] == "read"


def test_both_deployed_copies_match_the_template():
    """The drift check, for this workflow: the tenant's copy and the workspace root's are
    exactly what their own configuration renders."""
    tenant = Path(__file__).resolve().parent.parent
    roots = [tenant]
    for parent in tenant.parents:
        if (parent / ".vibey-gh.toml").is_file() and (parent / ".github/workflows").is_dir():
            roots.append(parent)
            break
    for root in roots:
        cfg = load_config(root)
        deployed = root / ".github/workflows/release-surfaces.yml"
        assert deployed.read_text(encoding="utf-8") == render_workflow(WORKFLOW, cfg), root


# ---------------------------------------------------------------------------------------
# `[announce]` is validated where it is read.


def test_the_announce_table_is_read_from_the_config_file(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[announce]\nmax_changes = 5\nwebhook_secret = 'HOOK'\n"
        "noise_patterns = ['^wip']\n[announce.groups]\nNew = ['feat']\n"
    )
    cfg = load_config(tmp_path).announce
    assert (cfg.max_changes, cfg.webhook_secret, cfg.noise_patterns) == (5, "HOOK", ("^wip",))
    assert cfg.groups == (("New", ("feat",)),)
    assert dict(cfg.type_words)["feat"] == "Feature"
    assert load_config(tmp_path.parent / "nowhere-at-all").announce == AnnounceConfig()


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"enabled": "yes"}, TypeError),
        ({"webhook_secret": "not a name"}, ValueError),
        ({"webhook_secret": 5}, ValueError),
        ({"username": " "}, ValueError),
        ({"username": 5}, ValueError),
        ({"username": "u" * 81}, ValueError),
        ({"max_changes": 0}, ValueError),
        ({"max_changes": True}, ValueError),
        ({"max_changes": "8"}, ValueError),
        ({"max_message_chars": 2001}, ValueError),
        ({"max_subject_chars": 10}, ValueError),
        ({"max_history_pages": 11}, ValueError),
        ({"max_history_candidates": 0}, ValueError),
        ({"max_history_candidates": 101}, ValueError),
        ({"webhook_secret": "GITHUB_TOKEN"}, ValueError),
        ({"webhook_secret": "github_hook"}, ValueError),
        ({"username": "Discord Bot"}, ValueError),
        ({"username": "clyde"}, ValueError),
        ({"username": "a@b"}, ValueError),
        ({"username": "a#b"}, ValueError),
        ({"username": "a:b"}, ValueError),
        ({"username": "x```"}, ValueError),
        ({"username": "everyone"}, ValueError),
        ({"username": " Here "}, ValueError),
        ({"breaking_group": 3}, TypeError),
        ({"groups": ((5, ("feat",)),)}, TypeError),
        ({"changelog_path": "CHANGES>).md"}, ValueError),
        ({"changelog_path": "docs/change log.md"}, ValueError),
        ({"other_group": "Breaking"}, ValueError),
        ({"breaking_group": " "}, ValueError),
        ({"groups": (("Added", ()),)}, ValueError),
        ({"groups": (("Added", ("Feat",)),)}, ValueError),
        ({"groups": (("A", ("feat",)), ("B", ("feat",)))}, ValueError),
        ({"type_words": (("feat", " "),)}, ValueError),
        ({"type_words": (("Feat", "x"),)}, ValueError),
        ({"noise_patterns": ("(",)}, ValueError),
        ({"changelog_path": "/abs"}, ValueError),
        ({"changelog_path": "../up"}, ValueError),
        ({"changelog_path": ""}, ValueError),
    ],
)
def test_a_bad_announce_value_is_refused(overrides, error):
    with pytest.raises(error):
        AnnounceConfig(**overrides)


@pytest.mark.parametrize(
    "table, message",
    [
        ({"groups": ["feat"]}, "announce.groups must be a table"),
        ({"groups": {"A": "feat"}}, "announce.groups must be a table"),
        ({"type_words": ["x"]}, "announce.type_words must be a table"),
        ({"type_words": {"feat": 1}}, "announce.type_words must be a table"),
        ({"noise_patterns": "x"}, "announce.noise_patterns must be a list"),
        ({"noise_patterns": [1]}, "announce.noise_patterns must be a list"),
    ],
)
def test_a_bad_announce_table_is_refused(table, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        AnnounceConfig.from_table(table)


def test_config_records_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        AnnounceConfig().max_changes = 3  # type: ignore[misc]


# ---------------------------------------------------------------------------------------
# Review of #1115, turned into tests: the reviewer's probes (r1115-probes/*.py), case by case.


def _run_history(tmp_path: Path, answers: dict[str, tuple[Any, str]], sha: str = HEAD):
    """`Announcer.run` over a scripted Actions API: what it posted and what it wrote for the
    workflow's marker step."""
    output = tmp_path / "github_output"
    output.unlink(missing_ok=True)
    history, _ = _history(answers)
    poster = RecordingPoster()
    Announcer(GhConfig(root=tmp_path), history, poster=poster, out=lambda _: None).run(
        _request(tmp_path, sha=sha), "https://127.0.0.1:9/hook", github_output=str(output)
    )
    return poster.sent[0][1]["content"].splitlines()[0], output.read_text()


def test_probe_range_a_an_unreadable_actions_api_leaves_the_watermark_unmoved(tmp_path):
    """The Actions API answers 502: the post goes out, says unknown, and `position=unknown`
    keeps the marker step from recording it, so the next run starts where the last recorded
    one did and the unread span is announced then (10.g)."""
    head, output = _run_history(
        tmp_path,
        {
            f"{_API}/actions/runs/99": (None, "HTTP 502 from the Actions API"),
            f"{_API}/commits/{HEAD}": ({"commit": {"message": "feat: new"}}, ""),
        },
    )
    assert "changes since: unknown (" in head and "HTTP 502" in ComposerEscape.plain(head)
    assert output == "posted=true\nposition=unknown\n"


@pytest.mark.parametrize(
    "failing",
    [
        {f"{_API}/actions/runs/4/jobs?per_page=100": (None, "HTTP 502")},
        {f"{_API}/compare/{BASE}...{HEAD}?per_page=100&page=1": (None, "HTTP 502")},
    ],
    ids=["jobs-listing", "compare"],
)
def test_a_failed_jobs_listing_or_compare_is_unknown_too(tmp_path, failing):
    answers = {
        _LIST: (_runs({"id": 4, "display_title": _title("develop", BASE)}), ""),
        f"{_API}/actions/runs/4/jobs?per_page=100": (_jobs("success"), ""),
        f"{_API}/commits/{HEAD}": ({"commit": {"message": "fix: head"}}, ""),
    } | failing
    _, output = _run_history(tmp_path, answers)
    assert output == "posted=true\nposition=unknown\n"


def test_probe_range_b_the_next_run_reads_from_the_last_recorded_position(tmp_path):
    """The run after an unknown one: its history has no accepted run at the unknown commit
    (the marker did not run there), so it starts from the last recorded one."""
    rng = {
        "status": "ahead",
        "total_commits": 2,
        "html_url": "u",
        "commits": [
            {"sha": "1" * 40, "commit": {"message": "feat: the span the unknown run skipped"}},
            {"sha": HEAD, "commit": {"message": "fix: head"}},
        ],
    }
    head, output = _run_history(
        tmp_path,
        {
            _LIST: (
                _runs(
                    {"id": 2, "display_title": _title("develop", "e" * 40)},
                    {"id": 1, "display_title": _title("develop", BASE)},
                ),
                "",
            ),
            f"{_API}/actions/runs/2/jobs?per_page=100": (_jobs("skipped"), ""),
            f"{_API}/actions/runs/1/jobs?per_page=100": (_jobs("success"), ""),
            f"{_API}/compare/{BASE}...{HEAD}?per_page=100&page=1": (rng, ""),
        },
    )
    assert f"changes since `{BASE[:12]}`" in head
    assert output == "posted=true\nposition=known\n"


def test_probe_range_c_a_force_push_re_anchors_and_says_so(tmp_path):
    diverged = {"status": "diverged", "total_commits": 3, "html_url": "u", "commits": []}
    head, output = _run_history(
        tmp_path,
        {
            _LIST: (_runs({"id": 1, "display_title": _title("develop", BASE)}), ""),
            f"{_API}/actions/runs/1/jobs?per_page=100": (_jobs("success"), ""),
            f"{_API}/compare/{BASE}...{HEAD}?per_page=100&page=1": (diverged, ""),
            f"{_API}/commits/{HEAD}": ({"commit": {"message": "fix: head"}}, ""),
        },
    )
    assert "re-anchored here (" in head and "history was rewritten" in head
    assert output == "posted=true\nposition=reanchored\n"


def test_probe_range_d_the_api_window_is_structural_and_named(tmp_path):
    """A status-filtered run listing stops at its 1000th result; ten full pages with nothing
    accepted re-anchor, naming the window rather than claiming there was no announcement."""
    other = [{"id": n, "display_title": _title("main", "d" * 40)} for n in range(100)]
    pages = {
        f"{_API}/actions/workflows/7/runs?status=success&per_page=100&page={page}": (
            _runs(*other),
            "",
        )
        for page in range(1, 11)
    }
    history, transport = _history(pages, pages=50)
    position = history.previous_position("develop", HEAD)
    assert position.structural and position.reason == (
        "no accepted announcement for develop in the last 1000 runs (the API's window)"
    )
    assert len([path for path in transport.asked if "workflows/7/runs" in path]) == 10


def test_a_long_run_of_unaccepted_runs_stops_early_and_re_anchors():
    """Each unaccepted run costs a jobs call; after `candidates` of them the history is
    structural. Staying unknown instead would never recover: every later run would find
    the same backlog and record nothing."""
    runs = [{"id": n, "display_title": _title("develop", f"{n:040x}")} for n in range(1, 6)]
    answers = {_LIST: (_runs(*runs), "")} | {
        f"{_API}/actions/runs/{n}/jobs?per_page=100": (_jobs("skipped"), "") for n in range(1, 6)
    }
    base = {f"{_API}/actions/runs/99": ({"workflow_id": 7}, "")}
    transport = ScriptedTransport(base | answers)
    history = ReleaseHistory(REPO, "99", transport=transport, candidates=3)
    position = history.previous_position("develop", HEAD)
    assert position == Position(
        None, "3 runs for develop since the last accepted announcement", structural=True
    )
    assert len([path for path in transport.asked if path.endswith("/jobs?per_page=100")]) == 3


def test_a_re_run_of_an_announced_commit_is_not_posted_again(tmp_path):
    out: list[str] = []
    poster = RecordingPoster()
    output = tmp_path / "github_output"
    Announcer(
        GhConfig(root=tmp_path),
        ScriptedHistory(position=Position(HEAD)),
        poster=poster,
        out=out.append,
    ).run(_request(tmp_path), _HOOK, github_output=str(output))
    assert poster.sent == []
    assert out == [f"announce: {HEAD[:12]} was already announced for develop; nothing posted"]
    assert output.read_text() == "posted=false\nposition=known\n"


def test_probe_leak_a_webhook_with_a_space_never_prints_its_token(tmp_path, capsys):
    """`http.client.InvalidURL` is not a URLError; it escaped `post` and its traceback
    printed the webhook's path. GitHub's masking misses a fragment of the secret."""
    url = "https://127.0.0.1:9/api/webhooks/123456/SECRET TOKEN-VALUE"
    history = ScriptedHistory(commits={HEAD: _commit("fix: probe", HEAD)})
    code = Announcer(GhConfig(root=tmp_path), history).run(_request(tmp_path), url)
    printed = capsys.readouterr()
    assert code == 0
    assert "::warning::announce: the Discord webhook post failed" in printed.out
    for fragment in ("TOKEN-VALUE", "SECRET", "123456"):
        assert fragment not in printed.out + printed.err


@pytest.mark.parametrize(
    "message",
    [
        (
            "InvalidURL: URL can't contain control characters. '/api/webhooks/1/SECRET TOKEN' "
            "(found at least ' ')"
        ),
        "error at /api/webhooks/77/elsewhere-token",
        "quoted /api/webhooks/1/SECRET%20TOKEN",
    ],
)
def test_redaction_removes_the_path_and_any_webhook_fragment(message):
    url = "https://discord.example/api/webhooks/1/SECRET TOKEN"
    redacted = DiscordWebhook.redact(message, url)
    assert "SECRET" not in redacted and "TOKEN" not in redacted.replace("<webhook>", "")
    assert "elsewhere-token" not in redacted
    assert DiscordWebhook.redact("x", "http://[bad") == "x"


def test_a_slashed_branch_and_tag_prefix_are_announced(tmp_path):
    """`release/next` is a branch git accepts (12.c); refs are URL-encoded into the path."""
    request = _request(tmp_path, branch="release/next")
    assert request.branch == "release/next"
    path = f"{_API}/compare/v%2F2.0.0...{HEAD}?per_page=100&page=1"
    history, transport = _history(
        {path: ({"status": "ahead", "total_commits": 0, "commits": []}, "")}
    )
    found, why = history.compare("v/2.0.0", HEAD)
    assert why == "" and found is not None and transport.asked[-1] == path
    cfg = dataclasses.replace(
        _release_repo(tmp_path), github_release=GithubReleaseConfig(tag_prefix="rel/")
    )
    content = _release(
        tmp_path,
        cfg,
        ScriptedHistory(
            ranges={("rel/2.0.0", HEAD): (CommitRange("ahead", 4, (), "https://cmp"), "")}
        ),
    )
    assert "4 commits since `rel/2.0.0`" in content


_PROBE_SUBJECTS = [
    "feat: @everyone ping",
    "feat: @\u200deveryone zwj",
    "fix: <@&123456789012345678> role",
    "fix: <#123> <t:1700000000:R> </cmd:1>",
    "fix: [x](javascript:alert(1)) masked",
    "fix: [x](<https://evil.example>) masked-angle",
    "fix: ***bold*** __u__ ~~s~~ ||spoiler|| `code` ```fence```",
    "fix: # heading -# subtext > quote",
    "fix: bidi \u202eRTL\u202c and \u2066iso\u2069 and ALM\u061cmark",
    "fix: tag chars \U000e0041\U000e0042 and vs\ufe0f and soft\u00adhyphen hangul\u3164fill",
    "fix: fillers \u115f\u1160\uffa0 and vs256 \U000e0100",
    "fix: :smile: <:custom:123> <a:anim:456>",
    "fix: close wrapper >) ](<https://evil>) (#12)",
    "fix: line\nbreak\r  \x85 NEL",
    "fix: trailing backslash \\",
    "fix: arabic-indic digits (#\u0661\u0662\u0663)",
]


def test_probe_escape_no_invisible_or_format_character_survives():
    composer = _composer(max_changes=50, max_subject_chars=400)
    records = [CommitRecord(f"{n:040x}", subject) for n, subject in enumerate(_PROBE_SUBJECTS)]
    content = composer.render("HEADER", composer.from_commits(records)).content
    blanks = {0x115F, 0x1160, 0x3164, 0xFFA0}
    for char in content:
        category = unicodedata.category(char)
        assert category not in ("Cc", "Cf") or char == "\n", f"U+{ord(char):04X}"
        assert ord(char) not in blanks and not 0xFE00 <= ord(char) <= 0xFE0F
        assert not 0xE0100 <= ord(char) <= 0xE01EF
    assert not re.search(r"(?<!\\)@everyone|(?<!\\)<[@#:ta/]", content)


def test_probe_escape_only_ascii_digits_make_a_pull_request_link():
    changes = _composer().from_commits([_commit("fix: digits (#\u0661\u0662\u0663)")])
    assert changes.changes[0].reference == "aaaaaaa"  # the commit, not a bogus link
    notes = _composer().from_changelog("## [1.0.0]\n\n### Fixed\n\n* x #\u0661\u0662\n", "1.0.0")
    assert notes is not None and notes.changes.changes[0].reference == ""


def test_probe_bound_random_inputs_stay_within_the_limit_quickly():
    rng = random.Random(7)
    alphabet = ["\U0001f4a9", "e\u0302\u0303", "*", "@", "<", "`", "|", "_", "\u202e", "a", " "]
    surfaces = [Surface(f"s{n}", f"https://o.github.io/r/develop/{n}.pdf") for n in range(7)]
    for _ in range(150):
        count = rng.choice([0, 1, 5, 50, 300])
        breaking = rng.randint(0, count)
        cfg = AnnounceConfig(
            max_message_chars=rng.choice([200, 500, 1999, 2000]),
            max_subject_chars=rng.choice([20, 40, 100, 400]),
            max_changes=rng.choice([1, 8, 50]),
        )
        composer = ChangelogComposer(cfg, "o/r", "https://github.com")
        records = [
            CommitRecord(
                f"{n:040x}",
                f"feat{'!' if n < breaking else ''}(s{n}): "
                + "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 600)))
                + f" (#{n})",
            )
            for n in range(count)
        ]
        message = composer.render(
            "H" * rng.choice([10, 150, 600]),
            composer.from_commits(records, unread=rng.randint(0, 5)),
            more_url="https://github.com/o/r/compare/a...b",
            more_label="compare",
            surfaces=surfaces,
        )
        assert _units(message.content) <= cfg.max_message_chars
        assert not any(0xD800 <= ord(char) <= 0xDFFF for char in message.content)


def test_probe_bound_five_thousand_breaking_changes_render_in_linear_time():
    """Measured in work, not seconds, so the check holds on a loaded machine: the old loop
    re-rendered every line for every line it dropped (quadratic; 5000 took 40 s). Now each
    change's line is rendered once per length level, plus the lines finally shown."""

    class Counting(ChangelogComposer):
        lines = 0

        def _line(self, change: Change, limit: int) -> str:
            Counting.lines += 1
            return super()._line(change, limit)

    composer = Counting(AnnounceConfig(), REPO, SERVER)
    records = [CommitRecord(f"{n:040x}", f"feat!: {'x' * 90} (#{n})") for n in range(5000)]
    message = composer.render("H", composer.from_commits(records))
    assert Counting.lines <= 3 * 5000 + message.listed
    assert _units(message.content) <= 2000
    assert f"**+{5000 - message.listed} more breaking changes**" in message.content


def test_the_surface_count_is_what_the_message_carries():
    composer = _composer()
    surfaces = [Surface("site", "https://s")]
    assert composer.render("h", ChangeSet(), surfaces=surfaces).surfaces == 1
    assert _composer(link_surfaces=False).render("h", ChangeSet(), surfaces=surfaces).surfaces == 0


def test_the_install_runs_apart_from_the_secrets(tmp_path):
    """The install step's build backend never runs beside the webhook or the token, and an
    old release without `announce` is upgraded rather than left in place."""
    steps = _rendered_workflow(tmp_path)["jobs"]["docs"]["steps"]
    names = [step.get("name") for step in steps]
    install = steps[names.index("Install the announcer")]
    announce = steps[names.index("Announce the published surfaces")]
    assert names.index("Install the announcer") + 1 == names.index(
        "Announce the published surfaces"
    )
    assert install["env"] == {"PIP_UPGRADE": "true"}
    assert "pip install" in install["run"] and "pip install" not in announce["run"]
    assert "DISCORD_WEBHOOK_URL" in announce["env"] and "GH_TOKEN" in announce["env"]


def test_breaking_changes_that_fit_once_shortened_are_all_listed():
    composer = _composer(link_pull_requests=False)
    records = [CommitRecord(f"{n:040x}", f"feat!: {'y' * 100} (#{n})") for n in range(20)]
    message = composer.render("h", composer.from_commits(records))
    assert message.listed == 20 and "more breaking" not in message.content
    lines = [line for line in message.content.splitlines() if line.startswith("- ")]
    assert all(len(line.split(" (#")[0]) < 70 for line in lines)
    assert _units(message.content) <= 2000


def test_a_control_character_becomes_a_space_and_a_format_character_nothing():
    text = "a" + chr(0x09) + "b" + chr(0x07) + "c" + chr(0x85) + "d" + chr(0x200D) + "e"
    assert ChangelogComposer.escape(text) == "a b c de"
