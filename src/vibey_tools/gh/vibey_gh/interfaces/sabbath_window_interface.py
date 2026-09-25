# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams for the Sabbath window (sub-doctrine 8.i; vibey ADR-0016)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol


class SunsetCalculatorInterface(Protocol):
    """Computes sunset for a civil date at a place."""

    def sunset(self, day: date, latitude: float, longitude: float) -> datetime | None:
        """The UTC instant of sunset on `day`, or None when the sun does not set there."""
        ...


class RestWindowInterface(Protocol):
    """One Sabbath: sundown Friday to sundown Saturday."""

    @property
    def opened(self) -> datetime: ...

    @property
    def resumes(self) -> datetime: ...

    @property
    def computed(self) -> bool:
        """True when both edges are computed sundowns, False when either is a fallback."""
        ...

    @property
    def basis(self) -> str:
        """How the edges were found, in words: computed, or which fallback and why."""
        ...

    def contains(self, at: datetime) -> bool: ...

    def report(self) -> str:
        """One line for a log: what is held, under which rule, and until when."""
        ...

    def summary(self) -> str:
        """The same fact as markdown for a job summary: paused, not failed (10.f)."""
        ...


class SabbathWindowInterface(Protocol):
    """Decides whether 8.i holds an instant."""

    @property
    def enabled(self) -> bool: ...

    @property
    def configured(self) -> bool: ...

    def window_for(self, friday: date) -> RestWindowInterface: ...

    def hold(self, at: datetime) -> RestWindowInterface | None:
        """The window holding `at`, or None when the caller may proceed."""
        ...

    def is_resting(self, at: datetime) -> bool: ...

    def next_resume(self, at: datetime) -> datetime: ...
