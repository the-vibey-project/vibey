# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of scripts/explorer_publish.py: declared here, consumed there (ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class PublishedProjectInterface(Protocol):
    """One project as the public explorer lists it."""

    @property
    def slug(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def project_id(self) -> str: ...


class ExplorerPublisherInterface(Protocol):
    """Writes the public, policy-scrubbed ledger of every project, and the registry."""

    async def publish(self, out: Path) -> Sequence[PublishedProjectInterface]: ...
