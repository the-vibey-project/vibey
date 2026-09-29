# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the skip-marker guard (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CommitMessage:
    """One commit as the guard reads it: who wrote it and what it says."""

    sha: str
    author_name: str
    author_email: str
    message: str


@dataclass(frozen=True)
class SkipMarkerFinding:
    """One place a skip marker was found: `where` names it for a person to act on."""

    where: str
    markers: tuple[str, ...]


@runtime_checkable
class SkipMarkerGuardInterface(Protocol):
    """Finds GitHub skip markers on their way into a permanent branch.

    A marker in a commit message, or in the title and body a squash merge turns into one,
    makes GitHub run no push workflow for the commit that carries it. On the release
    branch that is a release with no CI, no publish and no tag, and nothing red anywhere.
    """

    def markers_in(self, text: str) -> tuple[str, ...]:
        """Every marker `text` carries, lower-cased, each once, in the order found."""
        ...

    def commits(self, revisions: str, cwd: Path | None = None) -> tuple[CommitMessage, ...]:
        """Every commit in the git revision range `revisions`, oldest first."""
        ...

    def findings(
        self,
        *,
        title: str,
        body: str,
        commits: Sequence[CommitMessage],
        exempt_authors: Sequence[str],
        exemptions_apply: bool,
    ) -> tuple[SkipMarkerFinding, ...]:
        """Every place a marker was found. A commit by an exempt author is skipped only
        while `exemptions_apply`; the title and body are never exempt."""
        ...
