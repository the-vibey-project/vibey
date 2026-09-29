# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The skip-marker guard: nothing reaches a permanent branch carrying a skip-ci marker.

The markers below are assembled from pieces rather than written out, so that this file's
own history can never carry one into a commit message by copy and paste.
"""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
from pathlib import Path

import pytest

from vibey_gh import cli
from vibey_gh.config import GhConfig, SkipMarkersConfig, load_config
from vibey_gh.interfaces.skip_marker_guard_interface import (
    CommitMessage,
    SkipMarkerFinding,
    SkipMarkerGuardInterface,
)
from vibey_gh.skip_markers import SkipMarkerGuard

SKIP_CI = "[" + "skip ci]"
CI_SKIP = "[" + "ci skip]"
NO_CI = "[" + "no ci]"
SKIP_ACTIONS = "[" + "skip actions]"
ACTIONS_SKIP = "[" + "actions skip]"
TRAILER = "skip-" + "checks: true"


def commit(message: str, *, name: str = "Ada", email: str = "ada@example.com", sha: str = "a" * 40):
    return CommitMessage(sha, name, email, message)


def git(tmp_path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *args],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository(tmp_path: Path, messages: list[tuple[str, str]]) -> tuple[str, str]:
    """A throwaway repository: (base, head) around one commit per (author, message)."""
    git(tmp_path, "init", "-q", "-b", "develop")
    git(tmp_path, "config", "commit.gpgsign", "false")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base", "--author", "B <b@example.com>")
    base = git(tmp_path, "rev-parse", "HEAD")
    for author, message in messages:
        git(tmp_path, "commit", "-q", "--allow-empty", "-m", message, "--author", author)
    return base, git(tmp_path, "rev-parse", "HEAD")


# ------------------------------------------------------------------------- detection


@pytest.mark.parametrize("marker", [SKIP_CI, CI_SKIP, NO_CI, SKIP_ACTIONS, ACTIONS_SKIP])
def test_every_bracketed_spelling_is_found_anywhere_and_in_any_case(marker):
    guard = SkipMarkerGuard()
    assert guard.markers_in(f"chore: refresh {marker}") == (marker,)
    assert guard.markers_in(f"body\n\n* old subject {marker.upper()} quoted") == (marker,)


@pytest.mark.parametrize(
    "text",
    [f"fix: x\n\n{TRAILER}", "fix: x\n\nSkip-Checks:true", "fix: x\n\n  skip-checks:  TRUE  "],
)
def test_the_skip_checks_trailer_is_found_only_as_a_line_of_its_own(text):
    assert SkipMarkerGuard().markers_in(text) == (TRAILER,)


def test_prose_about_the_marker_is_not_a_marker():
    guard = SkipMarkerGuard()
    assert guard.markers_in("docs: explain the skip-ci marker and skip ci in prose") == ()
    assert guard.markers_in(f"docs: the words {TRAILER} mid-sentence") == ()
    assert guard.markers_in("") == ()


def test_each_marker_is_reported_once_in_the_order_found():
    text = f"{NO_CI} then {SKIP_CI} and {SKIP_CI.upper()} again\n{TRAILER}"
    assert SkipMarkerGuard().markers_in(text) == (NO_CI, SKIP_CI, TRAILER)


# -------------------------------------------------------------------------- findings


def test_title_body_and_every_commit_are_all_read():
    found = SkipMarkerGuard().findings(
        title=f"chore(release): 3.0.0 {SKIP_CI}",
        body=f"* chore(estimate): refresh delivery forecast {SKIP_CI}",
        commits=[commit("feat: clean"), commit(f"chore: tidy\n\n{TRAILER}", sha="b" * 40)],
        exempt_authors=(),
        exemptions_apply=True,
    )
    assert [f.where for f in found] == [
        "the pull request title",
        "the pull request body",
        f"commit {'b' * 12} (chore: tidy)",
    ]
    assert found[2].markers == (TRAILER,)


def test_an_exempt_author_may_mark_their_own_commits_into_the_integration_branch():
    bot = commit(f"chore(estimate): refresh {SKIP_CI}", name="estimate-bot", email="bot@x")
    guard = SkipMarkerGuard()
    by_email = guard.findings(
        title="t", body="", commits=[bot], exempt_authors=("bot@x",), exemptions_apply=True
    )
    by_name = guard.findings(
        title="t", body="", commits=[bot], exempt_authors=("estimate-bot",), exemptions_apply=True
    )
    assert by_email == by_name == ()


def test_an_exemption_never_reaches_the_release_branch_or_a_title_or_body():
    bot = commit(f"chore: {SKIP_CI}", email="bot@x")
    guard = SkipMarkerGuard()
    into_release = guard.findings(
        title="t", body="", commits=[bot], exempt_authors=("bot@x",), exemptions_apply=False
    )
    assert len(into_release) == 1
    title = guard.findings(
        title=f"x {SKIP_CI}",
        body="",
        commits=[bot],
        exempt_authors=("bot@x",),
        exemptions_apply=True,
    )
    assert [f.where for f in title] == ["the pull request title"]


def test_the_guard_and_its_records_honour_their_interface():
    assert isinstance(SkipMarkerGuard(), SkipMarkerGuardInterface)
    assert SkipMarkerFinding("x", (SKIP_CI,)).markers == (SKIP_CI,)


# ------------------------------------------------------------------------ git reading


def test_commits_are_read_oldest_first_with_their_authors_and_whole_messages(tmp_path):
    base, head = repository(
        tmp_path,
        [("Ada <ada@example.com>", "feat: one\n\nbody line"), ("Bot <bot@x>", f"chore: {SKIP_CI}")],
    )
    commits = SkipMarkerGuard().commits(f"{base}..{head}", cwd=tmp_path)
    assert [(c.author_name, c.author_email) for c in commits] == [
        ("Ada", "ada@example.com"),
        ("Bot", "bot@x"),
    ]
    assert commits[0].message.startswith("feat: one\n\nbody line")
    assert commits[1].sha == head


def test_an_empty_range_reads_no_commits(tmp_path):
    base, _ = repository(tmp_path, [])
    assert SkipMarkerGuard().commits(f"{base}..{base}", cwd=tmp_path) == ()


def test_an_unreadable_range_raises_rather_than_passing(tmp_path):
    repository(tmp_path, [])
    with pytest.raises(RuntimeError, match="git log"):
        SkipMarkerGuard().commits("nope..also-nope", cwd=tmp_path)


# ---------------------------------------------------------------------------- command


def guard_for(tmp_path: Path, **changes) -> SkipMarkerGuard:
    cfg = dataclasses.replace(GhConfig(root=tmp_path), **changes)
    return SkipMarkerGuard(config=lambda: cfg)


def test_a_clean_range_passes(tmp_path, capsys):
    base, head = repository(tmp_path, [("Ada <a@x>", "feat: clean")])
    assert guard_for(tmp_path).run(f"{base}..{head}", "feat: clean", "", "develop") == 0
    assert "no skip marker in 1 commit(s)" in capsys.readouterr().out


def test_a_marked_range_is_refused_with_every_place_named(tmp_path, capsys):
    base, head = repository(tmp_path, [("Ada <a@x>", f"chore: estimate {SKIP_CI}")])
    assert guard_for(tmp_path).run(f"{base}..{head}", f"t {NO_CI}", "", "main") == 1
    out = capsys.readouterr().out
    assert "the pull request title: " + NO_CI in out
    assert "(chore: estimate" in out
    assert "::error::A GitHub skip marker is on its way into a permanent branch" in out


def test_exemptions_follow_the_base_branch(tmp_path):
    base, head = repository(tmp_path, [("Bot <bot@x>", f"chore: {SKIP_CI}")])
    exempt = SkipMarkersConfig(exempt_authors=("bot@x",))
    guard = guard_for(tmp_path, skip_markers=exempt)
    assert guard.run(f"{base}..{head}", "t", "", "develop") == 0
    assert guard.run(f"{base}..{head}", "t", "", "main") == 1


def test_the_range_is_read_from_the_checkout_named_not_the_configuration(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    base, head = repository(target, [("Ada <a@x>", f"chore: {SKIP_CI}")])
    trusted = tmp_path / "automation"
    trusted.mkdir()
    assert guard_for(trusted).run(f"{base}..{head}", "", "", "develop", target) == 1


def test_an_unreadable_range_is_refused_not_passed(tmp_path, capsys):
    repository(tmp_path, [])
    assert guard_for(tmp_path).run("nope..nope", "", "", "develop") == 1
    assert "git log nope..nope" in capsys.readouterr().out


def test_a_disabled_guard_checks_nothing(tmp_path, capsys):
    guard = guard_for(tmp_path, skip_markers=SkipMarkersConfig(enabled=False))
    assert guard.run("does-not..matter", f"x {SKIP_CI}", "", "main") == 0
    assert "disabled" in capsys.readouterr().out


def test_the_cli_subcommand_dispatches_through_the_class(monkeypatch, tmp_path):
    seen: list[argparse.Namespace] = []
    monkeypatch.setattr(SkipMarkerGuard, "run", lambda self, *a: seen.append(a) or 0)
    status = cli.main(
        [
            "skip-marker-check",
            "--commits",
            "a..b",
            "--title",
            "T",
            "--body",
            "B",
            "--base",
            "main",
            "--checkout",
            str(tmp_path),
        ]
    )
    assert status == 0
    assert seen == [("a..b", "T", "B", "main", tmp_path)]


# ------------------------------------------------------------------------- config


def test_skip_markers_load_from_toml_and_exempt_nothing_by_default(tmp_path):
    assert load_config(tmp_path).skip_markers == SkipMarkersConfig(enabled=True, exempt_authors=())
    (tmp_path / ".vibey-gh.toml").write_text(
        '[skip_markers]\nenabled = false\nexempt_authors = ["bot@x"]\n', encoding="utf-8"
    )
    assert load_config(tmp_path).skip_markers == SkipMarkersConfig(False, ("bot@x",))


@pytest.mark.parametrize("authors", [("",), ("a", "a")])
def test_exempt_authors_must_be_unique_and_nonempty(authors):
    with pytest.raises(ValueError, match="skip_markers.exempt_authors"):
        SkipMarkersConfig(exempt_authors=authors)
