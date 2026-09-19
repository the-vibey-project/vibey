# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A complete in-memory reference implementation of the tier storage port."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from vibey.domain.interfaces.value_objects_interface import LedgerEventInterface
from vibey.infrastructure.ledger.interfaces.tier_store_interface import LedgerTierStoreInterface


@dataclass
class InMemoryLedgerTierStore(LedgerTierStoreInterface):
    """A lossless raw/compressed store used by tests and local demonstrations."""

    _raw: dict[UUID, dict[int, LedgerEventInterface]] = field(default_factory=dict)
    _compressed: dict[UUID, dict[int, bytes]] = field(default_factory=dict)

    def raw_events(self, project_id: UUID) -> Sequence[LedgerEventInterface]:
        return tuple(self._raw.get(project_id, {}).values())

    def put_raw(self, event: LedgerEventInterface) -> None:
        self._raw.setdefault(event.project_id, {})[event.seq] = event

    def remove_raw(self, project_id: UUID, seq: int) -> None:
        self._raw.get(project_id, {}).pop(seq, None)

    def compressed_record(self, project_id: UUID, seq: int) -> bytes | None:
        return self._compressed.get(project_id, {}).get(seq)

    def compressed_records(self, project_id: UUID) -> Sequence[tuple[int, bytes]]:
        return tuple(sorted(self._compressed.get(project_id, {}).items()))

    def put_compressed(self, project_id: UUID, seq: int, record: bytes) -> None:
        existing = self.compressed_record(project_id, seq)
        if existing is not None and existing != record:
            raise ValueError(f"compressed ledger record already exists at {project_id}:{seq}")
        self._compressed.setdefault(project_id, {})[seq] = record
