# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Infrastructure-internal seams.

These are not application ports -- nothing outside infrastructure/ implements
them. They live here so the `every class has an interface in interfaces/`
rule holds at every layer, not just the application boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from vibey.application.dto import RunSpec

if TYPE_CHECKING:  # concrete result types live beside their adapter
    from vibey.domain.ledger import LedgerEvent
    from vibey.infrastructure.engines.claudeloop_process import (
        ClaudeLoopResult,
        CommandResult,
    )
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class BoundedClaudeLoop(Protocol):
    async def run(self, spec: RunSpec, *, web_search: bool = False) -> ClaudeLoopResult: ...


@runtime_checkable
class CommandExecutor(Protocol):
    async def execute(self, argv: tuple[str, ...]) -> CommandResult: ...


@runtime_checkable
class EventAppender(Protocol):
    """Appends one ledger event on a connection the caller owns, so the
    append can join a transaction that is already open. `conn` is an asyncpg
    connection or pool proxy, typed `Any` because asyncpg publishes no
    structural type for either and this package declares seams rather than
    naming drivers."""

    async def append(self, conn: Any, draft: LedgerEventDraft) -> LedgerEvent: ...


__all__ = [
    "BoundedClaudeLoop",
    "CommandExecutor",
    "EventAppender",
]
