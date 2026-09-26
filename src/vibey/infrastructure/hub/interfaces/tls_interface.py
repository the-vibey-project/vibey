# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the hub's own TLS certificate.

Mirrors `vibey/infrastructure/hub/tls.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import datetime as _dt

    from vibey.infrastructure.hub.tls import HubTls


@runtime_checkable
class HubCertificateInterface(Protocol):
    """Makes the hub's self-signed certificate once and reports its fingerprint."""

    def ensure(self, names: frozenset[str], now: _dt.datetime) -> HubTls:
        """The certificate files and fingerprint, made on first call."""
        ...
