# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind gate notices on the ledger.

Mirrors `vibey/infrastructure/db/gate_notice_store.py` (ADR-0016). Interfaces declare; they
never consume. The domain and draft types are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.gate_notices import GateNoticeStore

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.domain.gate_notice import GateNotice
    from vibey.domain.phase import Phase
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class GateNoticeDraftBuilderInterface(Protocol):
    """Builds the `GateNotified` or `GateNoticeUndeliverable` draft for one notice."""

    def draft(
        self, notice: GateNotice, *, cycle: int, phase: Phase, at: datetime
    ) -> LedgerEventDraft: ...


@runtime_checkable
class PostgresGateNoticeStoreInterface(GateNoticeStore, Protocol):
    """Records each gate notice once per gate and notice number, fleet-wide."""
