# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/worker_processes.py` (ADR-0016). Interfaces declare; they never
consume."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.worker_processes import ProcessInfo, StopPlan, StopReport


@runtime_checkable
class ProcessTableInterface(Protocol):
    """What this machine is running, as the operating system's process table says."""

    def snapshot(self) -> Sequence[ProcessInfo]: ...


@runtime_checkable
class WorkerStopperInterface(Protocol):
    """Finds this user's `vibey worker` processes and stops them and what they started."""

    def plan(self) -> StopPlan: ...

    def stop(self, plan: StopPlan, *, grace_seconds: float) -> StopReport:
        """SIGTERM everything in the plan, wait up to `grace_seconds`, SIGKILL what is left."""
        ...
