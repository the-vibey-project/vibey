# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for managing ledger storage tiers (vibey#114).

A project's ledger grows forever. To avoid disk exhaustion, we move records through
three tiers: raw (standard), compressed (mid-tier), and archival.

This interface defines how to transition records between tiers and how to query
across them losslessly.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.interfaces.value_objects_interface import LedgerEventInterface


@runtime_checkable
class TierConfigInterface(Protocol):
    """The retention bounds used by a ledger tier manager."""

    @property
    def standard_n(self) -> int: ...

    @property
    def mid_tier_n(self) -> int: ...

    @property
    def archival_enabled(self) -> bool: ...


@runtime_checkable
class LedgerTierManagerInterface(Protocol):
    """Manages the movement and compression of ledger records across tiers."""

    def reconcile_tiers(self, project_id: UUID, config: TierConfigInterface) -> tuple[int, int]:
        """Move records through tiers based on the config. Returns (raw_count, compressed_count)."""
        ...

    def get_event(self, project_id: UUID, seq: int) -> LedgerEventInterface | None:
        """Fetch a single event, potentially decompressing it from a lower tier."""
        ...

    def get_range(
        self, project_id: UUID, from_seq: int, to_seq: int
    ) -> Sequence[LedgerEventInterface]:
        """Fetch a range of events across tiers losslessly."""
        ...
