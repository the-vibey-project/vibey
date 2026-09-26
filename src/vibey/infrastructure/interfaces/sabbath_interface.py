# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/sabbath.py` (ADR-0016). Interfaces declare; they never
consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from vibey.domain.sabbath import RestWindowInterface


class HostSabbathGateInterface(Protocol):
    """Sub-doctrine 8.i as this host keeps it (ADR-0070)."""

    def hold(self) -> RestWindowInterface | None:
        """The window holding now, or None when the caller may proceed."""
        ...

    def describe(self) -> list[str]:
        """The window, the zone and where the location came from, for a doctor."""
        ...

    def location_resolved(self) -> bool:
        """False when no source placed the host and the declared fallback times rule."""
        ...
