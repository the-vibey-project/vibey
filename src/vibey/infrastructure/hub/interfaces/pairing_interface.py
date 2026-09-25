# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind pairing devices and recording it in the ledger.

Mirrors `vibey/infrastructure/hub/pairing.py` and `pairing_ledger.py` (ADR-0016).
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from vibey.domain.hub_scope import HubScope
    from vibey.domain.ledger import EventKind


@runtime_checkable
class PairingLedgerInterface(Protocol):
    """Appends a pairing or revocation event to every project's ledger, atomically."""

    async def record(self, kind: EventKind, payload: Mapping[str, object], at: datetime) -> int:
        """Appends the event everywhere; the number of projects written."""
        ...


@runtime_checkable
class HubPairingInterface(Protocol):
    """Offers, claims, lists and revokes device pairings for one running hub."""

    def offer(self, scopes: frozenset[HubScope]) -> dict[str, object]:
        """A new 6-digit offer of `scopes`, with its expiry and pairing URI."""
        ...

    async def claim(self, code: str, name: str) -> dict[str, object]:
        """Spends the offer and pairs a device: its id, its key (once) and its scopes."""
        ...

    def devices(self) -> list[dict[str, object]]:
        """Every paired device, without its key."""
        ...

    async def revoke(self, device_id: str) -> bool:
        """Revokes the device at once; False when it was not paired."""
        ...
