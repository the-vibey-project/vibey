# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's port onto the units it keeps running and the hub they serve (ADR-0101).

Implemented by `infrastructure/acp/acp_service_units.py`, over `SupervisorInstaller` and the
planner's `acp_services`. Blocking: the caller runs each method off the loop. Interfaces
declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import UnitOutcome


@runtime_checkable
class ServiceUnitsInterface(Protocol):
    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        """Plan the units for `names` (`hub`, `worker`) and write each one's file, never
        replacing one the operator edited (`kept-differing`): one outcome per name, in order.
        The environment file the units read is created from its template when missing. Raises
        ValueError, naming the key to change, when no unit could run as configured."""
        ...

    def label(self, name: str) -> str:
        """The service manager's label for `name` (`<[supervisor] label_prefix>.<name>`).
        Raises ValueError when `[supervisor]` cannot be read."""
        ...

    def detached_hub_pid(self) -> int | None:
        """The process id a running hub recorded in `serving.json`, when that process is
        alive; None when there is no record, it is unreadable, or its process is gone."""
        ...

    def start_hub(self) -> bool:
        """Run `vibey hub start` once, stdin closed; whether it exited 0."""
        ...
