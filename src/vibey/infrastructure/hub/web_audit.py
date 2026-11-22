# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each use of the hub's web search and fetch, written to the ledger (ADR-0102, SP-ACP 9b).

A search or a fetch is recorded where its reader will look: on the ledger of the project the
caller named (`project_id`), else -- like a pairing (`pairing_ledger.py`), since the principal
could be working for any of them -- on every project's ledger, in one transaction. Filed under the
project's cycle and phase, no engine, no job, `trusted`: the hub did it. `vibey ledger search
--kind WebFetched` and the `vibey_ledger` tool find it.

With no project at all there is no ledger to write to, and the hub refuses the use rather than
make it unrecorded (`WebToolUnavailable`); a named project that does not exist is
`UnknownProject`. A project in a phase this vibey does not know refuses the write and the
transaction rolls back, so a record is never in some projects and silently missing from others
(writers stay strict, vibey#287).

Declared by `interfaces/web_audit_interface.py`; the port it fills is the application's
`WebAuditPortInterface`.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.web_tools import WebToolUnavailable
from vibey.infrastructure.db.interfaces import EventAppenderInterface, ProjectRowMapperInterface
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_EVERY: Final = "SELECT * FROM project ORDER BY id FOR KEY SHARE"
_ONE: Final = "SELECT * FROM project WHERE id = $1 FOR KEY SHARE"
_ANY: Final = "SELECT EXISTS (SELECT 1 FROM project)"
_EXISTS: Final = "SELECT EXISTS (SELECT 1 FROM project WHERE id = $1)"
NO_LEDGER: Final = (
    "the hub has no project ledger to record this use in, and it searches or fetches nothing "
    "it cannot record: name a project_id, or start a project first"
)


class PostgresWebAudit:
    """Declared by `interfaces/web_audit_interface.py::WebAuditInterface`."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
        correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    ) -> None:
        self._pool = pool
        self._appender = appender
        self._rows = rows
        self._correlation = correlation

    async def ready(self, project_id: UUID | None) -> None:
        async with self._pool.acquire() as conn:
            if project_id is None:
                if not await conn.fetchval(_ANY):
                    raise WebToolUnavailable(NO_LEDGER)
            elif not await conn.fetchval(_EXISTS, project_id):
                raise UnknownProject(f"no project {project_id}")

    async def record(
        self,
        kind: EventKind,
        payload: Mapping[str, object],
        at: datetime,
        project_id: UUID | None,
    ) -> int:
        body = dict(payload)
        written = 0
        async with self._pool.acquire() as conn, conn.transaction():
            rows = (
                await conn.fetch(_EVERY)
                if project_id is None
                else await conn.fetch(_ONE, project_id)
            )
            if not rows:
                if project_id is not None:
                    raise UnknownProject(f"no project {project_id}")
                raise WebToolUnavailable(NO_LEDGER)
            for row in rows:
                project = self._rows.to_record(row)
                if not isinstance(project.phase, Phase):
                    raise WrongPhase(
                        f"project {project.project_id} is in phase {project.phase.value!r}, "
                        "which this vibey does not know; it will not record a web use there"
                    )
                await self._appender.append(
                    conn,
                    LedgerEventDraft(
                        project_id=project.project_id,
                        cycle=project.cycle,
                        phase=project.phase,
                        kind=kind,
                        engine_id=None,
                        job_id=None,
                        causation_id=None,
                        correlation_id=self._correlation.for_project(project.project_id).value,
                        provenance=Provenance.TRUSTED,
                        produced_at=at,
                        payload=body,
                        digest=digest_event(body),
                    ),
                )
                written += 1
        return written
