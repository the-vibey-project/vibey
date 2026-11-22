# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each use of the hub's web search and fetch, written to the ledger (ADR-0102, SP-ACP 9b).

A search or a fetch is recorded on the ledger of the **latest** project -- the one `vibey ledger
search` and `vibey ledger show` read when no project is named -- and, when the caller named a
project (`project_id`), on that project's too, deduplicated, in one transaction. The caller can
add a ledger, never take the latest away: a model steered to name some old project cannot keep
its record out of the person's default view. Filed under each project's cycle and phase, no
engine, no job, `trusted`: the hub did it. `vibey ledger search --kind WebFetched` finds it.

`ready` checks everything `record` needs before the hub acts: a latest project exists (else
`WebToolUnavailable`: no ledger to write to), a named project exists (else `UnknownProject`), and
every target is in a phase this vibey knows (else `WebToolUnavailable`), so the write that
follows the act fails only for a cause `ready` cannot see (the database itself). `record`
refuses the same way and rolls back: a record is never on one ledger and missing from another.

Declared by `interfaces/web_audit_interface.py`; the port it fills is the application's
`WebAuditPortInterface`.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final
from uuid import UUID

import asyncpg

from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import UnknownProject
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.web_tools import WebToolUnavailable
from vibey.infrastructure.db.interfaces import EventAppenderInterface, ProjectRowMapperInterface
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_LATEST: Final = "SELECT * FROM project ORDER BY created_at DESC, id DESC LIMIT 1"
"""The latest project, chosen exactly as `ProjectRepository.get_latest` chooses it."""
_ONE: Final = "SELECT * FROM project WHERE id = $1"
_LOCK: Final = " FOR KEY SHARE"
NO_LEDGER: Final = (
    "the hub has no project ledger to record this use in, and it searches or fetches nothing "
    "it cannot record: start a project first"
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
            await self._targets(conn, project_id, lock=False)

    async def record(
        self,
        kind: EventKind,
        payload: Mapping[str, object],
        at: datetime,
        project_id: UUID | None,
    ) -> int:
        body = dict(payload)
        async with self._pool.acquire() as conn, conn.transaction():
            projects = await self._targets(conn, project_id, lock=True)
            for project in projects:
                await self._appender.append(
                    conn,
                    LedgerEventDraft(
                        project_id=project.project_id,
                        cycle=project.cycle,
                        phase=project.phase,  # type: ignore[arg-type]  # checked by _targets
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
        return len(projects)

    async def _targets(self, conn: Any, project_id: UUID | None, *, lock: bool) -> list[Any]:
        """The latest project, and the named one when it is another, each in a phase this vibey
        knows; or the refusal that says which is missing."""
        tail = _LOCK if lock else ""
        latest = await conn.fetchrow(_LATEST + tail)
        if latest is None:
            raise WebToolUnavailable(NO_LEDGER)
        rows = [latest]
        if project_id is not None and project_id != latest["id"]:
            named = await conn.fetchrow(_ONE + tail, project_id)
            if named is None:
                raise UnknownProject(f"no project {project_id}")
            rows.append(named)
        projects = [self._rows.to_record(row) for row in rows]
        for project in projects:
            if not isinstance(project.phase, Phase):
                raise WebToolUnavailable(
                    f"project {project.project_id} is in a phase this vibey does not know, so the "
                    "hub cannot record a web use there and makes none; upgrade vibey"
                )
        return projects
