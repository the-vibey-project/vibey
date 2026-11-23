# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a marketplace's manifest (SP-LOOPS Task 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.marketplace_catalog import MarketplaceCatalog


@runtime_checkable
class MarketplaceManifestInterface(Protocol):
    def read(self, root: Path) -> MarketplaceCatalog:
        """The plugins `<root>/.claude-plugin/marketplace.json` lists. Raises `ManifestError`,
        reading nothing past the manifest, when any plugin's source is absolute, climbs out of
        `root`, or resolves (through a symlink) outside it, and when the manifest itself is
        missing, too large, outside `root` or malformed. A plugin that cannot be used here but
        is not hostile (a remote source, a missing folder) is listed in `skipped` instead."""
        ...
