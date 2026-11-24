# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The values `infrastructure/loops/` hands back (SP-LOOPS Task 7). Records with no behaviour, so no
seams of their own (ADR-0016)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vibey_runners.common.capabilities.lock_entry import LockEntry

from vibey.application.dto import PruneReport


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


# `PruneReport` moved to `application/dto.py` (SP-LOOPS Phase 4, Task 8): BUILD's capability
# service, in the application layer, returns it from its sweep and may not import this module.
# Re-exported so the path the pruner and `vibey loops snapshots prune` use does not break.
__all__ = ["FetchResult", "MarketplaceUpdate", "PruneReport"]
