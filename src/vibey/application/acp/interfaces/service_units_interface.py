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
        """Plan the units for `names` (`hub`, `worker`) and write each one's file: one outcome
        per name, in order. A unit vibey wrote before (its recorded digest) is replaced; one the
        operator edited is kept as it is (`kept-differing`). The environment file the units read
        is created from its template when missing. Raises ValueError, naming the key to change,
        when no unit could run as configured, or `OSError` when a file cannot be written."""
        ...

    def waiting(self, name: str) -> str:
        """What the service `name` still needs before it can run (the worker: a database in the
        environment file); "" when nothing."""
        ...

    def recorded(self) -> tuple[str, ...]:
        """The labels whose unit vibey wrote and still has a record of."""
        ...

    def remove(self, label: str) -> UnitOutcome:
        """Delete the unit file of `label` only while it is exactly what vibey wrote: `removed`,
        `absent` (already gone), `kept-differing` (edited, or never vibey's), or `failed`."""
        ...

    def label(self, name: str) -> str:
        """The service manager's label for `name` (`<[supervisor] label_prefix>.<name>`).
        Raises ValueError when `[supervisor]` cannot be read."""
        ...

    def detached_hub_pid(self) -> int | None:
        """Whether a hub runs outside the service manager: None when nothing holds the hub's
        lock (`serve.lock`); else the pid its holder wrote, or 0 when it wrote none."""
        ...

    def start_hub(self) -> bool:
        """Run `vibey hub start` once, stdin closed, in the user's configuration folder; whether
        it exited 0."""
        ...
