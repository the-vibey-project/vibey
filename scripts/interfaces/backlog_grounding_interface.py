# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `scripts/backlog_grounding.py` declares it needs and gives."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class RepositoryInterface(Protocol):
    """The tracked tree, read the way a person would before changing it."""

    def tracked(self) -> Sequence[str]:
        """Every tracked path, repository-relative."""
        ...

    def excerpt(self, path: str, lines: int) -> tuple[int, str]:
        """(total line count, the first `lines` lines) of a tracked text file."""
        ...

    def grep(self, term: str, limit: int) -> Sequence[str]:
        """Up to `limit` `path:line:text` hits for a fixed string, across tracked files."""
        ...

    def text(self, path: str) -> str:
        """A tracked file in full."""
        ...


class IssueGroundingInterface(Protocol):
    """Turns an issue's text into the facts a small model would otherwise have to go and find."""

    def ground(self, issue: str) -> str:
        """The files the issue names (with excerpts), where its identifiers occur, and the
        repository's non-negotiables, each bounded and each cut loudly (ADR-0075)."""
        ...
