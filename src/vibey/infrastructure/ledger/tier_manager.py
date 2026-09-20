# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lossless ledger tier coordination (vibey#114).

The manager never invents an empty history. A physical store is required at
construction time; reconciliation writes and verifies the compressed copy before
removing a raw copy, and all reads search both tiers.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast
from uuid import UUID

from vibey.domain.interfaces.ledger_record_interface import LedgerRecordCodecInterface
from vibey.domain.interfaces.ledger_tier_interface import (
    LedgerTierManagerInterface,
    TierConfigInterface,
)
from vibey.domain.interfaces.value_objects_interface import LedgerEventInterface
from vibey.domain.ledger import LedgerEvent
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.infrastructure.ledger.compression import DEFAULT_CODEC
from vibey.infrastructure.ledger.interfaces.compression_interface import (
    CompressionCodecInterface,
)
from vibey.infrastructure.ledger.interfaces.tier_store_interface import LedgerTierStoreInterface


class TierRecordError(ValueError):
    """A compressed tier record failed its lossless decode or identity check."""


class TierManager(LedgerTierManagerInterface):
    """Move and read ledger events across an injected raw/compressed store."""

    def __init__(
        self,
        store: LedgerTierStoreInterface,
        codec: CompressionCodecInterface = DEFAULT_CODEC,
        records: LedgerRecordCodecInterface = LEDGER_RECORDS,
    ) -> None:
        self._store = store
        self._codec = codec
        self._records = records

    def reconcile_tiers(self, project_id: UUID, config: TierConfigInterface) -> tuple[int, int]:
        """Compress all but the newest ``standard_n`` events, then verify each copy.

        The current store port exposes one lossless compressed tier. ``mid_tier_n`` and
        ``archival_enabled`` remain policy inputs for a future physical archival store;
        no record is discarded merely because that store is not configured.
        """
        raw = sorted(self._store.raw_events(project_id), key=lambda event: event.seq)
        keep_raw = max(config.standard_n, 0)
        candidates = raw[:-keep_raw] if keep_raw else raw
        for event in candidates:
            record = self._encode(event)
            existing = self._store.compressed_record(project_id, event.seq)
            if existing is None:
                self._store.put_compressed(project_id, event.seq, self._codec.compress(record))
            restored = self.get_event(project_id, event.seq)
            if restored is None or restored.project_id != project_id or restored.seq != event.seq:
                raise TierRecordError(
                    f"compressed ledger record failed verification at {project_id}:{event.seq}"
                )
            self._store.remove_raw(project_id, event.seq)
        return len(self._store.raw_events(project_id)), len(
            self._store.compressed_records(project_id)
        )

    def get_event(self, project_id: UUID, seq: int) -> LedgerEventInterface | None:
        """Read raw first, then decompress and strictly decode the lower tier."""
        raw = next(
            (event for event in self._store.raw_events(project_id) if event.seq == seq), None
        )
        if raw is not None:
            return raw
        compressed = self._store.compressed_record(project_id, seq)
        if compressed is None:
            return None
        try:
            event = self._records.from_fields(
                json.loads(self._codec.decompress(compressed).decode("utf-8"))
            )
        except Exception as exc:  # noqa: BLE001 - every codec reports corrupt bytes differently
            raise TierRecordError(
                f"invalid compressed ledger record at {project_id}:{seq}"
            ) from exc
        if event.project_id != project_id or event.seq != seq:
            raise TierRecordError(f"compressed ledger identity mismatch at {project_id}:{seq}")
        return event

    def get_range(
        self, project_id: UUID, from_seq: int, to_seq: int
    ) -> Sequence[LedgerEventInterface]:
        """Return one ordered, deduplicated view across raw and compressed tiers."""
        if from_seq > to_seq:
            return ()
        events: dict[int, LedgerEventInterface] = {}
        for event in self._store.raw_events(project_id):
            if from_seq <= event.seq <= to_seq:
                events[event.seq] = event
        for seq, _ in self._store.compressed_records(project_id):
            if from_seq <= seq <= to_seq:
                decoded = self.get_event(project_id, seq)
                if decoded is not None:
                    events[seq] = decoded
        return tuple(events[seq] for seq in sorted(events))

    def _encode(self, event: LedgerEventInterface) -> bytes:
        fields = self._records.to_fields(cast(LedgerEvent, event))
        return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
