"""What the lane watchdog promises, declared beside `lane_watchdog.py` (sub-doctrine 9.b).

Declares; never consumes. `tests/meta/test_storm_lane_watchdog.py` holds each class to its
Protocol, so the declaration cannot drift from the class it describes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LaneLimitsInterface(Protocol):
    """Every limit a lane runs under, in seconds: finite and positive, declared in storm.toml."""

    attempt_seconds: float
    lane_seconds: float
    stall_seconds: float
    poll_seconds: float
    grace_seconds: float


@runtime_checkable
class AttemptOutcomeInterface(Protocol):
    """How one watched attempt ended: exited, timeout, stalled or stopped."""

    reason: str
    returncode: int | None
    elapsed_seconds: float
    silent_seconds: float
    last_event_at: str | None
    verdict: dict[str, Any] | None


@runtime_checkable
class AttemptWatchdogInterface(Protocol):
    """Runs one attempt in a session of its own and ends it when a limit is crossed."""

    def watch(
        self, argv: list[str], *, cwd: Path, events: Path, budget_seconds: float
    ) -> AttemptOutcomeInterface:
        """Run `argv` to its end or to a limit; its tree never outlives the call."""
        ...

    def terminate(self, process: subprocess.Popen[bytes]) -> None:
        """Stop the attempt's group and every session it reported."""
        ...

    def signallable(self, group: int) -> bool:
        """Whether `group` may be signalled as one of an attempt's own process groups."""
        ...


@runtime_checkable
class LaneAttemptsInterface(Protocol):
    """The attempts of one lane, under one lane-wide wall clock."""

    def run(self, attempt: int, plan: str) -> dict[str, Any] | None:
        """One attempt as a result.json record; None once the lane's clock is spent."""
        ...


@runtime_checkable
class ChildGuardInterface(Protocol):
    """The attempt child's half of the private report channel."""

    def record_escaping_subprocesses(self) -> None:
        """Report every subprocess started in a new session, the moment it exists."""
        ...

    def report(self, verdict: dict[str, Any]) -> None:
        """Send the attempt's verdict to the parent."""
        ...

    def die_with(self, parent_pid: int) -> None:
        """Stop the attempt if the lane that started it disappears."""
        ...
