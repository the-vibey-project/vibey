# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for publishing a ledger: the shard, and the site built from it.

Mirrors `vibey/application/ledger_publication.py` (ADR-0016). Interfaces declare;
they never consume. The ports the use cases drive -- where a shard is kept, where a
site is written -- are declared with the other ledger seams in
`application/interfaces/ledger.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.interfaces.publication_policy_interface import TrimCountsInterface
from vibey.domain.ledger import LedgerEvent
from vibey.domain.publication_policy import WithheldReason

if TYPE_CHECKING:
    # Only a property names it, and the module it lives in imports this one: a
    # runtime import would be a cycle. Every method annotation resolves at runtime
    # (tests/application/test_interfaces_convention.py).
    from vibey.application.ledger_publication import ShardHolding


@runtime_checkable
class ShardHeaderInterface(Protocol):
    """What a shard is, where it came from, and everything the policy withheld."""

    @property
    def format(self) -> str:
        """The shard format's name and version."""
        ...

    @property
    def project_id(self) -> UUID: ...

    @property
    def project_name(self) -> str: ...

    @property
    def holds(self) -> ShardHolding:
        """The whole ledger from its first event, or a window of it."""
        ...

    @property
    def tier(self) -> str:
        """Which storage tier served the events (vibey#114); honest until tiers exist."""
        ...

    @property
    def ledger_first_seq(self) -> int | None:
        """The first seq the shard covers, withheld events included; None when empty."""
        ...

    @property
    def ledger_last_seq(self) -> int | None:
        """The last seq the shard covers, withheld events included; None when empty."""
        ...

    @property
    def ledger_event_count(self) -> int:
        """Events the shard covers, published and withheld."""
        ...

    @property
    def chain_scheme(self) -> str: ...

    @property
    def chain_head(self) -> str:
        """The ledger's own chain link at `ledger_last_seq`, over every event."""
        ...

    @property
    def chain_findings(self) -> int:
        """Disagreements the chain walk found in the ledger; zero means verified."""
        ...

    @property
    def policy_scheme(self) -> str: ...

    @property
    def policy_fingerprint(self) -> str:
        """The exact rules that made the shard."""
        ...

    @property
    def published_count(self) -> int: ...

    @property
    def published_digest_range(self) -> str:
        """`digest_range` over the published records, as published."""
        ...

    @property
    def withheld(self) -> Mapping[WithheldReason, int]:
        """Events withheld whole, by reason; every reason present."""
        ...

    @property
    def trimmed(self) -> TrimCountsInterface:
        """What was removed from inside published records, summed."""
        ...

    @property
    def trims(self) -> Mapping[UUID, TrimCountsInterface]:
        """By event id, what was removed from each record the policy changed."""
        ...

    @property
    def events_withheld(self) -> int:
        """Events withheld for any reason."""
        ...


@runtime_checkable
class LedgerShardInterface(Protocol):
    """The shard a repository holds: its header, then its published records."""

    @property
    def header(self) -> ShardHeaderInterface: ...

    @property
    def records(self) -> tuple[LedgerEvent, ...]:
        """Published records, in seq order."""
        ...


@runtime_checkable
class LedgerSitePlanInterface(Protocol):
    """The static JSON surface for one shard, before anything is written."""

    @property
    def shard(self) -> LedgerShardInterface: ...

    @property
    def documents(self) -> Mapping[str, Mapping[str, object]]:
        """Every JSON document, by its relative POSIX path in the site."""
        ...


@runtime_checkable
class SearchTokenizerInterface(Protocol):
    """Turns a payload into the words a client-side search matches."""

    def tokens(self, payload: Mapping[str, object]) -> tuple[str, ...]:
        """Lower-cased words from every string and number, each once, sorted."""
        ...


@runtime_checkable
class LedgerExporterInterface(Protocol):
    """Reads one project's ledger and writes the shard the public may see."""

    def shard(
        self, project_id: UUID, project_name: str, events: Sequence[LedgerEvent]
    ) -> LedgerShardInterface:
        """The shard for these events. Pure."""
        ...

    async def export(self, project_id: UUID, project_name: str, out: Path) -> LedgerShardInterface:
        """Read the project's whole ledger, build its shard, and write it to `out`."""
        ...


@runtime_checkable
class LedgerSiteBuilderInterface(Protocol):
    """Builds the static JSON surface from a shard. Needs no database."""

    def plan(self, shard: LedgerShardInterface) -> LedgerSitePlanInterface:
        """Check the shard and lay out every document. Raises `InvalidLedgerShard`."""
        ...

    def build(self, source: Path, out: Path) -> LedgerSitePlanInterface:
        """Read the shard at `source`, plan it, and write the site into `out`."""
        ...
