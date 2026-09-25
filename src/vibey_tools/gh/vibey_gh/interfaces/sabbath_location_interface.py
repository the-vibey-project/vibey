# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams for resolving where this machine stands (sub-doctrine 8.i; vibey ADR-0016)."""

from __future__ import annotations

from typing import Protocol


class ResolvedLocationInterface(Protocol):
    """A place, its source, and how far it may be off (10.f)."""

    @property
    def latitude(self) -> float: ...

    @property
    def longitude(self) -> float: ...

    @property
    def source(self) -> str: ...

    @property
    def accuracy_km(self) -> float: ...

    @property
    def coarse(self) -> bool:
        """True when the place is only a zone's reference city: the window then widens."""
        ...

    def describe(self) -> str: ...


class LocationSourceInterface(Protocol):
    """One way of finding the host: an override, an OS service, or the zone table."""

    def locate(self) -> ResolvedLocationInterface | None:
        """The place, or None when this source is absent or cannot answer. Never raises."""
        ...
