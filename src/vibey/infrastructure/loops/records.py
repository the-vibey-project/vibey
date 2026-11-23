# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The values `infrastructure/loops/` hands back (SP-LOOPS Task 7). Records with no behaviour, so no
seams of their own (ADR-0016)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vibey_runners.common.capabilities.lock_entry import LockEntry


@dataclass(frozen=True, slots=True)
class FetchResult:
    """What a fetcher put in its folder: the commit a git fetch checked out (None for a local
    folder), and the paths it left out (a symlink is never copied), relative to the tree."""

    commit: str | None
    left_out: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MarketplaceUpdate:
    """One `marketplace update`: the entry written to the lock, the folder it pins, and what the
    fetch said."""

    entry: LockEntry
    root: Path
    fetched: FetchResult


@dataclass(frozen=True, slots=True)
class PruneReport:
    """What `snapshots prune` removed, and what it would not touch and why."""

    removed: tuple[Path, ...]
    refused: tuple[tuple[Path, str], ...]
