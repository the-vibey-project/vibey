# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams for the sovereign heartbeat and the readiness it is published on (ADR-0016).

A heartbeat is a claim that the sovereign lane can take a job now. `LaneReadinessInterface`
is what the claim is checked against before it is made, so a test hands the heartbeat an
exact answer -- serving or not, and why -- instead of a runner and a model endpoint.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LaneStateInterface(Protocol):
    """Whether the sovereign lane can serve right now, and the sentence that says why."""

    @property
    def serving(self) -> bool: ...

    @property
    def reason(self) -> str: ...


@runtime_checkable
class LaneReadinessInterface(Protocol):
    """Reads, never assumes, whether the sovereign lane can serve."""

    def assess(self) -> LaneStateInterface:
        """Serving only when every check read a positive answer; a check that could not be
        read is a reason the lane is not serving, never a pass."""
        ...


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
    """Publishes the heartbeat when the lane can serve, and reads its age."""

    def beat(self, readiness: LaneReadinessInterface) -> ReadinessInterface:
        """Publish only when `readiness` says the lane can serve; otherwise push nothing and
        say why. Never raises: every failure comes back as a reason."""
        ...

    def probe(self, *, max_age_minutes: int, now: float | None = None) -> ReadinessInterface:
        """Whether a heartbeat younger than `max_age_minutes` is on the remote."""
        ...
