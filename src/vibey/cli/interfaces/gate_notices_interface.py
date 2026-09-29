# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey gates --remind` and `vibey doctor`'s gate-notices line.

Mirrors `vibey/cli/gate_notices.py` (ADR-0016). Interfaces declare; they never consume. The
types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager
    from uuid import UUID

    from vibey.application.dto import GateReminderReport
    from vibey.cli.gate_notices import GateReaders


@runtime_checkable
class GateRemindersPresenterInterface(Protocol):
    """Renders one reminder sweep: for a person first, a program second."""

    def lines(self, report: GateReminderReport) -> list[str]: ...

    def json(self, report: GateReminderReport) -> str: ...


@runtime_checkable
class GateRemindersCommandInterface(Protocol):
    """Runs `vibey gates --remind`."""

    async def run(self, project_id: UUID | None, *, as_json: bool, dry_run: bool) -> None:
        """Exits 1 when `project_id` names no project, or when any project's notices could
        not be read."""
        ...


@runtime_checkable
class GateNoticeDoctorInterface(Protocol):
    """`vibey doctor`'s gate-notices line."""

    async def line(self) -> str:
        """`PASS`, `WARN` (gates nobody will be told about) or `UNKNOWN`, never raising."""
        ...


@runtime_checkable
class GateReadersOpenerInterface(Protocol):
    """Opens the open-gate and project readers `vibey doctor` counts from."""

    def open(self, dsn: str) -> AbstractAsyncContextManager[GateReaders]: ...
