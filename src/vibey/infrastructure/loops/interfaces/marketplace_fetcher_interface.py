# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over putting a marketplace's tree in a staging folder (SP-LOOPS Task 7).

Implemented by `git_marketplace_fetcher.py` (git sources) and `local_marketplace_copier.py`
(absolute folders). Interfaces declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.domain.marketplace_source import MarketplaceSource
from vibey.infrastructure.loops.records import FetchResult


@runtime_checkable
class MarketplaceFetcherInterface(Protocol):
    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        """Puts the tree of `source` (at `ref`, for git) in `into`, a folder this call makes
        0700 and that must not exist yet. The tree holds no git metadata; a symlink git checks
        out stays a link (nothing follows it: a run's copy leaves it out and names it), and a
        local copy leaves links out and lists them in `left_out`. Raises `MarketplaceFetchError` naming why, for a source of another kind too; what it
        wrote is then the caller's to remove (it is inside the caller's staging folder)."""
        ...
