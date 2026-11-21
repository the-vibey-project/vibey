# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ACP sessions and their logs in PostgreSQL (SP-ACP, migration 0023).

Both tables are append-only by trigger, and the application role holds only `SELECT` and
`INSERT` on them (`ledger_guard.APP_ROLE_GRANTS`): everything this needs. An append is one
statement that inserts, or -- when the `(session_id, seq)` is taken -- reports whether the row
there is the same event, so a resend is answered as stored and a different event at that `seq`
is a `SessionEventConflict`, never an overwrite.

A list is a keyset over `(updated_at, session_id)` descending, where `updated_at` is the newest
event's `recorded_at` (the session's `created_at` before any). A row tuple comparison against
the cursor, never a time comparison alone, so sessions sharing one instant neither repeat nor
fall between pages.

Declared by `application/acp/interfaces/acp_session_repository_interface.py`.
"""

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

import asyncpg

from vibey.application.acp.dto import SessionEvent, SessionRecord
from vibey.domain.acp.session_log import SessionEventConflict

_CREATE: Final = """
INSERT INTO acp_session (session_id, cwd, created_by) VALUES ($1, $2, $3)
ON CONFLICT (session_id) DO NOTHING
"""

# The outer SELECT reads the snapshot from before the insert, so `same` sees only a row that
# was already there.
_APPEND: Final = """
WITH inserted AS (
    INSERT INTO acp_session_event (session_id, seq, kind, payload)
    VALUES ($1, $2, $3, $4::jsonb)
    ON CONFLICT (session_id, seq) DO NOTHING
    RETURNING 1
)
SELECT EXISTS (SELECT 1 FROM inserted) AS inserted,
       EXISTS (
           SELECT 1 FROM acp_session_event
           WHERE session_id = $1 AND seq = $2 AND kind = $3 AND payload = $4::jsonb
       ) AS same
"""

# Read again, in a statement of its own, only when the append found neither: a concurrent
# identical append that committed after the first statement's snapshot is seen here.
_SAME: Final = """
SELECT kind = $3 AND payload = $4::jsonb FROM acp_session_event
WHERE session_id = $1 AND seq = $2
"""

_EVENTS: Final = """
SELECT seq, kind, payload FROM acp_session_event
WHERE session_id = $1 AND seq > $2
ORDER BY seq
LIMIT $3
"""

_LIST: Final = """
WITH listed AS (
    SELECT s.session_id, s.cwd,
           COALESCE(
               (SELECT max(e.recorded_at) FROM acp_session_event e
                WHERE e.session_id = s.session_id),
               s.created_at
           ) AS updated_at,
           (SELECT e.payload->>'title' FROM acp_session_event e
            WHERE e.session_id = s.session_id AND e.kind = 'title'
            ORDER BY e.seq DESC LIMIT 1) AS title,
           COALESCE(
               (SELECT e.kind = 'closed' FROM acp_session_event e
                WHERE e.session_id = s.session_id
                ORDER BY e.seq DESC LIMIT 1),
               false
           ) AS closed
    FROM acp_session s
    WHERE s.created_by = $1 AND ($2::text IS NULL OR s.cwd = $2)
)
SELECT session_id, cwd, updated_at, title, closed FROM listed
WHERE $3::timestamptz IS NULL OR (updated_at, session_id) < ($3::timestamptz, $4::text)
ORDER BY updated_at DESC, session_id DESC
LIMIT $5
"""

_OWNER: Final = "SELECT created_by, cwd FROM acp_session WHERE session_id = $1"


class PostgresAcpSessionRepository:
    """Declared by `application/acp/interfaces/acp_session_repository_interface.py`."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, session_id: str, cwd: str, created_by: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE, session_id, cwd, created_by)

    async def append(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
    ) -> bool:
        document = json.dumps(dict(payload))
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_APPEND, session_id, seq, kind, document)
            stored = row is not None and (row["inserted"] or row["same"])
            if not stored:
                stored = bool(await conn.fetchval(_SAME, session_id, seq, kind, document))
        if not stored:
            raise SessionEventConflict(
                f"session {session_id} already holds another event at seq {seq}"
            )
        return True

    async def events_after(
        self, session_id: str, after: int, limit: int
    ) -> tuple[SessionEvent, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_EVENTS, session_id, after, limit)
        return tuple(
            SessionEvent(seq=row["seq"], kind=row["kind"], payload=json.loads(row["payload"]))
            for row in rows
        )

    async def list(
        self,
        created_by: str,
        *,
        cwd: str | None,
        cursor: tuple[datetime, str] | None,
        limit: int,
    ) -> tuple[SessionRecord, ...]:
        stamp, after = cursor if cursor is not None else (None, None)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_LIST, created_by, cwd, stamp, after, limit)
        return tuple(
            SessionRecord(
                session_id=row["session_id"],
                cwd=row["cwd"],
                title=row["title"],
                updated_at=row["updated_at"],
                closed=row["closed"],
            )
            for row in rows
        )

    async def owner(self, session_id: str) -> tuple[str, str] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_OWNER, session_id)
        return (row["created_by"], row["cwd"]) if row is not None else None
