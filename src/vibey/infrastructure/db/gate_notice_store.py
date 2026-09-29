# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices on the ledger: `GateNotified` and `GateNoticeUndeliverable`.

A notice is recorded once per gate and notice number, fleet-wide. In one transaction the
store takes an advisory lock on that identity, reads whether either kind is on record for
it -- whoever wrote it -- and appends only when neither is. Two sweeps racing on one gate
decide one after the other, and the second writes nothing. The event is filed under the
project's cycle and phase as they stand when it lands, with no engine and no job of its
own -- the gate's job is in the payload, as `GateAnswered` files it -- and is `trusted`: vibey's own account of what it sent. The application role holds
`SELECT` and `INSERT` on the ledger (`ledger_guard.APP_ROLE_GRANTS`): everything this needs.

Declared by `interfaces/gate_notice_store_interface.py` (ADR-0016).
"""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.gate_notice import GateNotice
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    GateNoticeDraftBuilderInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft

type _Connection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection

NOTICE_KINDS: Final = (EventKind.GATE_NOTIFIED.value, EventKind.GATE_NOTICE_UNDELIVERABLE.value)

_LOCK_KEY: Final = "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))"

_PROJECT: Final = "SELECT cycle, phase FROM project WHERE id = $1"

# Read by the project's (project_id, kind, seq) index; the notice number is compared as
# text, so a payload no vibey wrote as a notice never fails the cast.
_ON_RECORD: Final = """
SELECT 1 FROM event
WHERE project_id = $1 AND kind = ANY($2::text[])
  AND payload->>'gate_id' = $3 AND payload->>'notice' = $4
LIMIT 1
"""

_RECORDED: Final = """
SELECT payload->>'gate_id' AS gate_id, payload->>'notice' AS notice FROM event
WHERE project_id = $1 AND kind = ANY($2::text[])
"""


class GateNoticeDraftBuilder:
    """Turns one notice into its ledger draft. Stateless."""

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def draft(
        self, notice: GateNotice, *, cycle: int, phase: Phase, at: datetime
    ) -> LedgerEventDraft:
        payload = notice.payload()
        return LedgerEventDraft(
            project_id=notice.project_id,
            cycle=cycle,
            phase=phase,
            kind=notice.event_kind,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=self._correlation.for_project(notice.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )


GATE_NOTICE_DRAFTS: Final[GateNoticeDraftBuilderInterface] = GateNoticeDraftBuilder()


class PostgresGateNoticeStore:
    """Records gate notices, once each, and reads which are on record."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        drafts: GateNoticeDraftBuilderInterface = GATE_NOTICE_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
    ) -> None:
        self._pool = pool
        self._drafts = drafts
        self._appender = appender

    async def record(self, notice: GateNotice) -> bool:
        gate_id = str(notice.gate_id)
        number = str(notice.notice)
        async with self._project(notice.project_id) as (conn, cycle, phase, now):
            await conn.execute(_LOCK_KEY, f"vibey.gate_notice:{gate_id}:{number}")
            if await conn.fetchval(
                _ON_RECORD, notice.project_id, list(NOTICE_KINDS), gate_id, number
            ):
                return False
            await self._appender.append(
                conn, self._drafts.draft(notice, cycle=cycle, phase=phase, at=now)
            )
            return True

    async def recorded(self, project_id: UUID) -> Mapping[UUID, frozenset[int]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_RECORDED, project_id, list(NOTICE_KINDS))
        found: dict[UUID, set[int]] = {}
        for row in rows:
            try:
                gate_id, number = UUID(row["gate_id"]), int(row["notice"])
            except (TypeError, ValueError):
                continue  # not a payload any vibey wrote as a notice
            found.setdefault(gate_id, set()).add(number)
        return {gate_id: frozenset(numbers) for gate_id, numbers in found.items()}

    @asynccontextmanager
    async def _project(
        self, project_id: UUID
    ) -> AsyncIterator[tuple[_Connection, int, Phase, datetime]]:
        """One transaction, and the project's current cycle and phase to file under."""
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(_PROJECT, project_id)
            if row is None:
                raise LookupError(f"no project {project_id} to record a gate notice under")
            now = await conn.fetchval("SELECT now()")
            yield conn, row["cycle"], Phase(row["phase"]), now
