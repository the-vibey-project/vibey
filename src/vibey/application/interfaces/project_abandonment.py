# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Abandoning a project's seams (`vibey abandon`): the store that moves a project into
abandoned atomically with everything it stops, and the one service every entry point
abandons a project through.

Mirrors `vibey/application/project_abandonment.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import AbandonmentReport


@runtime_checkable
class ProjectAbandonmentStore(Protocol):
    """Abandons one project. Reached only through `ProjectAbandonmentInterface`, which
    checks the reason and the label first."""

    async def preview(self, project_id: UUID) -> AbandonmentReport:
        """What `abandon` would do now, writing nothing: the unsettled jobs it would
        cancel and the open gates it would withdraw. Raises `UnknownProject`, and
        `AbandonmentRefused` for a project that cannot be abandoned."""
        ...

    async def abandon(
        self, project_id: UUID, *, reason: str, by: str, account: str
    ) -> AbandonmentReport:
        """Locks the project's row and, in ONE transaction: withdraws every open gate of
        the project, cancels every unsettled job, moves the project into abandoned
        through the guarded compare-and-set, and appends its `PhaseTransitioned` and one
        `GateWithdrawn` per gate -- so a crash leaves all of it as it was. A project
        already abandoned writes nothing. Raises `UnknownProject`, and
        `AbandonmentRefused` for a project that cannot be abandoned."""
        ...


@runtime_checkable
class ProjectAbandonmentInterface(Protocol):
    """The operator's clean exit for a project that is not going to finish."""

    async def preview(
        self, project_id: UUID, *, reason: str, by: str | None = None
    ) -> AbandonmentReport:
        """A dry run: checks what the real run checks, and writes nothing."""
        ...

    async def abandon(
        self, project_id: UUID, *, reason: str, by: str | None = None
    ) -> AbandonmentReport:
        """Abandons the project. `by` names who, for the record -- a label, not an
        authority -- and defaults to the account running the command, which is recorded
        beside it. Raises `InvalidAbandonment` before anything is written for a reason
        or label that cannot be recorded."""
        ...
