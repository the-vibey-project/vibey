# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_session_service.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import SessionEvent, SessionRecord
    from vibey.application.dto import HubPrincipal


@runtime_checkable
class AcpSessionServiceInterface(Protocol):
    """The hub's side of ACP session persistence: each call authorised, each session kept to
    the principal that created it."""

    async def create(self, principal: HubPrincipal, session_id: str, cwd: str) -> None:
        """Keep a session for `principal` under `cwd`. Creating it again with the same folder
        changes nothing; another principal's session, or another folder, is refused."""
        ...

    async def append(
        self,
        principal: HubPrincipal,
        session_id: str,
        seq: int,
        kind: str,
        payload: Mapping[str, Any],
    ) -> bool:
        """Append one event to `principal`'s session; True once it is stored."""
        ...

    async def events(
        self,
        principal: HubPrincipal,
        session_id: str,
        *,
        after: int,
        limit: int,
        cwd: str | None,
    ) -> tuple[SessionEvent, ...]:
        """`principal`'s session's events after `after`; when `cwd` is given, only for a
        session kept under that folder."""
        ...

    async def list(
        self, principal: HubPrincipal, *, cwd: str | None, cursor: str | None, limit: int
    ) -> tuple[tuple[SessionRecord, ...], str | None]:
        """A page of `principal`'s sessions, newest first, and the opaque cursor of the next
        page (None after the last)."""
        ...
