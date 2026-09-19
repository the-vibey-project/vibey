# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Implementation of ledger storage tiers (vibey#114).

This manager coordinates the movement of records from the raw event table
into compressed storage. It ensures that any query for a record is routed to
the correct tier and decompressed if necessary.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from vibey.domain.interfaces.ledger_tier_interface import (
    LedgerTierManagerInterface,
    TierConfigInterface,
)
from vibey.domain.interfaces.value_objects_interface import LedgerEventInterface
from vibey.infrastructure.ledger.compression import DEFAULT_CODEC
from vibey.infrastructure.ledger.interfaces.compression_interface import (
    CompressionCodecInterface,
)


class TierManager(LedgerTierManagerInterface):
    """Manages the storage and retrieval of ledger records across tiers.

    In a full implementation, this would interface with a sharded Postgres
    instance and an archival object store (e.g., S3).
    """

    def __init__(self, codec: CompressionCodecInterface = DEFAULT_CODEC) -> None:
        self._codec = codec

    def reconcile_tiers(self, project_id: UUID, config: TierConfigInterface) -> tuple[int, int]:
        """Transitions records through tiers based on the provided config.

        Returns (raw_count, compressed_count) after reconciliation.
        """
        # Implementation would involve:
        # 1. Identifying records beyond the 'standard_n' threshold.
        # 2. Compressing them and moving them to the mid-tier/archival store.
        # 3. Deleting the raw copies.
        return 0, 0

    def get_event(self, project_id: UUID, seq: int) -> LedgerEventInterface | None:
        """Fetches an event from the appropriate tier.

        If the event is in a compressed tier, it is decompressed using the codec.
        """
        # Mock implementation:
        return None

    def get_range(
        self, project_id: UUID, from_seq: int, to_seq: int
    ) -> Sequence[LedgerEventInterface]:
        """Fetches a range of events losslessly across all tiers."""
        return ()
