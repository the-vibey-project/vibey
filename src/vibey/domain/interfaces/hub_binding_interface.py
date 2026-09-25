# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind where the hub listens and which `Host` it answers.

Mirrors `vibey/domain/hub_binding.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.hub_binding import Exposure


@runtime_checkable
class HubBindingPolicyInterface(Protocol):
    """Loopback by default; the LAN only when declared; `Host` from an allowlist."""

    def is_loopback(self, host: str) -> bool:
        """True for `localhost`, 127.0.0.0/8 and ::1."""
        ...

    def resolve(self, requested: str | None, *, lan_declared: bool) -> str:
        """The address to bind, or `UndeclaredExposure` for an undeclared LAN address."""
        ...

    def exposure(self, bound: str, *, lan_declared: bool) -> Exposure:
        """Loopback, declared LAN, or undeclared, for a hub bound to `bound`."""
        ...

    def allowed_hosts(self, port: int, names: frozenset[str]) -> frozenset[str]:
        """Every `Host` value the hub answers on `port`."""
        ...

    def admits(self, host_header: str | None, allowed: frozenset[str]) -> bool:
        """True only for a present `Host` in `allowed`."""
        ...
