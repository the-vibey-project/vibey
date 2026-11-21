# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the hub keeps ACP sessions and their logs (SP-ACP, migration 0023).

Implemented by `infrastructure/db/acp_session_repository.py`. Both tables are append-only by
trigger (`public.ledger_refuse_rewrite()`), as the ledger is. Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.application.acp.dto import SessionEvent, SessionRecord


@runtime_checkable
class AcpSessionRepositoryInterface(Protocol):
    async def create(self, session_id: str, cwd: str, created_by: str, *, limit: int) -> bool:
        """Keep a session while `created_by` holds fewer than `limit`. True when it was kept
        now; False when it was not -- the id was already kept (a second create changes
        nothing), or `created_by` already holds `limit` sessions."""
        ...

    async def append(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any], *, limit: int
    ) -> bool:
        """Append one event while the session holds fewer than `limit`. True when it was
        written, or when the same event is already there (a replay); `SessionEventConflict`
        when another event holds that `seq`; `AcpSessionLimitReached` when the session is full.
        Nothing already kept is ever dropped or changed."""
        ...

    async def events_after(
        self, session_id: str, after: int, limit: int
    ) -> tuple[SessionEvent, ...]:
        """At most `limit` events with a `seq` after `after`, oldest first."""
        ...

    async def list(
        self,
        created_by: str,
        *,
        cwd: str | None,
        cursor: tuple[datetime, str] | None,
        limit: int,
    ) -> tuple[SessionRecord, ...]:
        """At most `limit` of `created_by`'s sessions (only those kept under `cwd`, when one is
        given), newest first by `(updated_at, session_id)`, after `cursor` when one is given:
        a keyset, so equal times neither repeat nor skip a session between pages."""
        ...

    async def owner(self, session_id: str) -> tuple[str, str] | None:
        """Who created the session and the folder it was kept under; None when there is no
        such session."""
        ...
