# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the merge train's protected paths (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol


class ProtectedPathsInterface(Protocol):
    """Decides whether a pull request touches a path only a human may merge.

    `[merge_train] protected_paths` names files the train must never merge unattended --
    the tests that prove the rest of the code works, say. The train's `--admin` fallback
    would otherwise bypass the code-owner review a ruleset demands for them, so the
    refusal has to happen before any merge is attempted, not be left to the forge.
    """

    def touched(self, patterns: Sequence[str], paths: Iterable[str]) -> tuple[str, ...]:
        """Every path in `paths` some pattern matches, sorted, each once."""
        ...

    def parse_listing(self, text: str) -> tuple[tuple[str, ...], int]:
        """(every path named, the number of files) from the paginated REST listing of a
        pull request's files. A rename contributes its old path as well as its new one."""
        ...

    def refusal(self, pr: Mapping[str, Any], patterns: Sequence[str]) -> str | None:
        """Why `pr` needs a human merge, or `None` when it touches no protected path --
        and a reason, never `None`, when its files could not all be listed."""
        ...
