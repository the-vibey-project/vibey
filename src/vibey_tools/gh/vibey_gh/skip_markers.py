# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Refuse a GitHub skip marker on its way into a permanent branch (`[skip_markers]`).

GitHub runs no `push` or `pull_request` workflow for a commit whose message carries one of
`config.SKIP_MARKERS`, or a `skip-checks: true` trailer. That is a convenience on a topic
branch and a silent outage on a permanent one: the 3.0.0 promotion was squash-merged by
hand, GitHub's default squash body concatenated 221 commit messages, several of them
quoted an old estimate subject carrying the marker, and every push workflow on `main` --
CI, the publish, the tag, the documentation -- was skipped without anything turning red.

So the guard reads everything that can become a commit on the base branch: every commit
message in the pull request's range, and the title and body a squash merge proposes. On a
merge queue's group the range is the group's own commits, which already carry the squash
title and body. A commit by an author in `[skip_markers] exempt_authors` may carry a marker
on its own message -- for an automation that deliberately skips CI on its bookkeeping --
but never into the release branch, whose push is the publish, and never in a title or body
a person merges.

What it cannot do is run where GitHub has already declined to run: a pull request whose
HEAD commit carries the marker gets no `pull_request` run at all. The check then never
reports, and a required check that never reports blocks the merge -- closed, not open, and
the remedy is the same one this guard names.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from vibey_gh.config import SKIP_MARKERS, GhConfig, load_config
from vibey_gh.interfaces.skip_marker_guard_interface import (
    CommitMessage,
    SkipMarkerFinding,
    SkipMarkerGuardInterface,
)

__all__ = ["SkipMarkerGuard"]

_BRACKETED = re.compile("|".join(re.escape(marker) for marker in SKIP_MARKERS), re.IGNORECASE)
# A trailer is a line of its own; GitHub accepts it with or without the space.
_TRAILER = re.compile(r"^[ \t]*skip-checks:[ \t]*true[ \t]*$", re.IGNORECASE | re.MULTILINE)
_TRAILER_NAME = "skip-checks: true"
# Unit and record separators: a commit message may hold any printable text, never these.
_FIELD = "\x1f"
_RECORD = "\x1e"


class SkipMarkerGuard(SkipMarkerGuardInterface):
    """Implements `SkipMarkerGuardInterface`."""

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        git: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._config = config
        self._git = git

    def markers_in(self, text: str) -> tuple[str, ...]:
        found = [match.group(0).lower() for match in _BRACKETED.finditer(text)]
        if _TRAILER.search(text):
            found.append(_TRAILER_NAME)
        return tuple(dict.fromkeys(found))

    def commits(self, revisions: str, cwd: Path | None = None) -> tuple[CommitMessage, ...]:
        run = self._git(
            [
                "git",
                "log",
                "--reverse",
                f"--format=%H{_FIELD}%an{_FIELD}%ae{_FIELD}%B{_RECORD}",
                revisions,
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode:
            # Refused, not passed: a range the guard could not read is a range it never
            # checked, and "no marker found" about commits it never saw is a false green.
            raise RuntimeError(f"git log {revisions}: {run.stderr.strip()}")
        found = []
        for record in run.stdout.split(_RECORD):
            record = record.lstrip("\n")
            if not record:
                continue
            sha, name, email, message = record.split(_FIELD, 3)
            found.append(CommitMessage(sha, name, email, message))
        return tuple(found)

    def findings(
        self,
        *,
        title: str,
        body: str,
        commits: Sequence[CommitMessage],
        exempt_authors: Sequence[str],
        exemptions_apply: bool,
    ) -> tuple[SkipMarkerFinding, ...]:
        found: list[SkipMarkerFinding] = []
        for where, text in (("the pull request title", title), ("the pull request body", body)):
            markers = self.markers_in(text)
            if markers:
                found.append(SkipMarkerFinding(where, markers))
        exempt = set(exempt_authors) if exemptions_apply else set()
        for commit in commits:
            if exempt & {commit.author_name, commit.author_email}:
                continue
            markers = self.markers_in(commit.message)
            if markers:
                # A marker is never whitespace, so a message carrying one has a first line.
                subject = commit.message.strip().splitlines()[0]
                found.append(SkipMarkerFinding(f"commit {commit.sha[:12]} ({subject})", markers))
        return tuple(found)

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--commits",
            required=True,
            metavar="BASE..HEAD",
            help="the git revision range whose commit messages are checked",
        )
        parser.add_argument("--title", default="", help="the pull request title, if any")
        parser.add_argument("--body", default="", help="the pull request body, if any")
        parser.add_argument(
            "--base",
            default="",
            help="the branch the change merges into; exemptions never apply to the release branch",
        )
        parser.add_argument(
            "--checkout",
            type=Path,
            default=None,
            help="the clone holding the range (default: this repository). A workflow runs "
            "from its trusted checkout, so the configuration read is never the pull "
            "request's own, and points here at the pull request's clone",
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        return cls().run(args.commits, args.title, args.body, args.base, args.checkout)

    def run(
        self, revisions: str, title: str, body: str, base: str, checkout: Path | None = None
    ) -> int:
        """Print every finding and return the exit status: 0 clean, 1 refused."""
        cfg = self._config()
        if not cfg.skip_markers.enabled:
            print("vibey-gh: [skip_markers] is disabled; nothing checked")
            return 0
        try:
            commits = self.commits(revisions, cwd=checkout or cfg.root)
        except RuntimeError as exc:
            print(f"vibey-gh: {exc}")
            return 1
        found = self.findings(
            title=title,
            body=body,
            commits=commits,
            exempt_authors=cfg.skip_markers.exempt_authors,
            exemptions_apply=base != cfg.release_branch,
        )
        if not found:
            print(f"vibey-gh: no skip marker in {len(commits)} commit(s), the title or the body")
            return 0
        for finding in found:
            print(f"  {finding.where}: {', '.join(finding.markers)}")
        print(
            "::error::A GitHub skip marker is on its way into a permanent branch. GitHub runs "
            "no push workflow for a commit that carries one -- no CI, no publish, no tag -- "
            "and nothing turns red to say so. Remove it from every place listed above "
            "(reword the commit, or edit the pull request title or body), or quote the idea "
            'in prose ("the skip-ci marker") instead of the marker itself.'
        )
        return 1
