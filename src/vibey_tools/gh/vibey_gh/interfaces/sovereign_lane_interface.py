# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the sovereign lane's readiness, beside `vibey_gh.sovereign_lane` (ADR-0016).

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
