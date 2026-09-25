# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/driver/file_ledger.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from vibey.domain.failover import FailoverKind, FailoverRecord


@runtime_checkable
class JsonlDriverLedgerInterface(Protocol):
    def records(self) -> tuple[FailoverRecord, ...]: ...

    def append(
        self, kind: FailoverKind, *, at: datetime, payload: Mapping[str, object]
    ) -> None: ...

    def verify_chain(self) -> bool: ...
