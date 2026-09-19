# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Storage port used by the ledger tier manager.

The manager owns tier policy and compression; this port owns the physical stores.
Keeping the port explicit prevents an unconfigured manager from pretending that an
empty answer is a valid ledger history.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.interfaces.value_objects_interface import LedgerEventInterface


@runtime_checkable
class LedgerTierStoreInterface(Protocol):
    """Raw events and their verified compressed representations."""

    def raw_events(self, project_id: UUID) -> Sequence[LedgerEventInterface]: ...

    def put_raw(self, event: LedgerEventInterface) -> None: ...

    def remove_raw(self, project_id: UUID, seq: int) -> None: ...

    def compressed_record(self, project_id: UUID, seq: int) -> bytes | None: ...

    def compressed_records(self, project_id: UUID) -> Sequence[tuple[int, bytes]]: ...

    def put_compressed(self, project_id: UUID, seq: int, record: bytes) -> None: ...
