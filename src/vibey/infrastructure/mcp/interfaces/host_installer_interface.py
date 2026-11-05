# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for building and applying `vibey connect` plans on disk (ADR-0100)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.host_clients import ConnectPlanItem


@runtime_checkable
class HostInstallerInterface(Protocol):
    def build_plan(self, requested: Sequence[str] | None = None) -> tuple[ConnectPlanItem, ...]:
        """Build the connection plan for the requested clients (or all when None/empty)."""
        ...

    def apply_plan(self, plan: Sequence[ConnectPlanItem]) -> None:
        """Write backups and merged configuration files for every non-unchanged item in `plan`."""
        ...
