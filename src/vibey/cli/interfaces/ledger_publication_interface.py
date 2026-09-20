# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey ledger export` and `vibey ledger site`.

Mirrors `vibey/cli/ledger_publication.py` (ADR-0016). Interfaces declare; they never
consume. The types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    from vibey.application.interfaces.ledger_publication_interface import (
        LedgerShardInterface,
        LedgerSitePlanInterface,
    )


@runtime_checkable
class PublicationPresenterInterface(Protocol):
    """Says, in lines a person reads, what was published and what was withheld."""

    def exported(self, shard: LedgerShardInterface, out: Path) -> list[str]:
        """What the export wrote, every count of what it withheld, and the chain head."""
        ...

    def built(self, plan: LedgerSitePlanInterface, out: Path) -> list[str]:
        """What the site build wrote, and every count of what the shard withheld."""
        ...


@runtime_checkable
class LedgerExportCommandInterface(Protocol):
    """Resolves the project, exports its shard, prints what happened."""

    async def run(self, project_id: UUID, out: Path, *, billing: bool = False) -> None:
        """Exit 1 for an unknown project."""
        ...


@runtime_checkable
class LedgerSiteCommandInterface(Protocol):
    """Builds the static site from a shard file, with no database."""

    def run(self, source: Path, out: Path, *, json_only: bool) -> None:
        """A usage error without `json_only`; exit 1 for a file that is not a shard."""
        ...
