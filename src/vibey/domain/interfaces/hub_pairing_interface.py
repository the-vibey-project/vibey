# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind pairing a device and checking what its requests prove.

Mirrors `vibey/domain/hub_pairing.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.hub_pairing import PairingOffer
    from vibey.domain.hub_scope import HubScope


@runtime_checkable
class HubPairingPolicyInterface(Protocol):
    """Offers codes, judges claims, and fixes what a device signs."""

    def offer(self, digits: str, scopes: frozenset[HubScope], now: float) -> PairingOffer:
        """An offer of `scopes` under `digits`; refuses a malformed code or an empty grant."""
        ...

    def claims(self, offer: PairingOffer, code: str, now: float) -> bool:
        """True when `code` matches the unexpired offer, compared in constant time."""
        ...

    def fresh(self, timestamp: float, now: float) -> bool:
        """True when a signed request's timestamp is within the window of `now`."""
        ...

    def canonical(
        self,
        *,
        device_id: str,
        method: str,
        path: str,
        query: str,
        timestamp: str,
        nonce: str,
        body_sha256: str,
    ) -> bytes:
        """The bytes a device signs for one request."""
        ...

    def uri(self, *, host: str, port: int, fingerprint: str, code: str) -> str:
        """The pairing URI the host shows as a QR code."""
        ...
