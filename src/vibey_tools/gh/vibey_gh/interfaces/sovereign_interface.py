# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the sovereign heartbeat, beside `vibey_gh.sovereign` (ADR-0016).

The readiness a heartbeat is published on has its own seam beside `vibey_gh.sovereign_lane`,
`interfaces/sovereign_lane_interface.py`; it is named here only because `beat()` takes it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_gh.interfaces.sovereign_lane_interface import (
    LaneReadinessInterface,
    LaneStateInterface,
)

__all__ = [
    "LaneReadinessInterface",
    "LaneStateInterface",
    "ReadinessInterface",
    "SovereignHeartbeatInterface",
]


@runtime_checkable
class ReadinessInterface(Protocol):
    """A heartbeat's outcome, or the probe's verdict on one."""

    @property
    def ready(self) -> bool: ...

    @property
    def reason(self) -> str: ...

    @property
    def age_seconds(self) -> int | None: ...


@runtime_checkable
class SovereignHeartbeatInterface(Protocol):
    """Publishes the heartbeat through a gate when the lane can serve, and reads its age."""

    def beat(self, readiness: LaneReadinessInterface) -> ReadinessInterface:
        """Publish only from a repository with a pre-push gate, and only when `readiness`
        says the lane can serve; otherwise push nothing and say why. Never raises: every
        failure, a readiness that raises included, comes back as a reason."""
        ...

    def probe(self, *, max_age_minutes: int, now: float | None = None) -> ReadinessInterface:
        """Whether a heartbeat younger than `max_age_minutes` is on the remote."""
        ...
