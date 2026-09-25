# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed ULTRA controls (ADR-0063): the operator's start, Stop and no-cap
declaration, each one trusted ledger event.

One transaction per control: lock the project's row `FOR NO KEY UPDATE` (so two
controls never interleave and a running worker's ledger writes are never blocked, as
`project_budget_store.py` explains), then append the event on the same connection,
filed under the project's cycle and phase as the locked row holds them. `trusted`
because only vibey's own host command writes these kinds.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import ClassVar, Final
from uuid import UUID

import asyncpg

from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import EventAppenderInterface, ProjectRowMapperInterface
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_LOCK_PROJECT: Final = "SELECT * FROM project WHERE id = $1 FOR NO KEY UPDATE"

ULTRA_CONTROL_KINDS: Final = frozenset(
    {EventKind.ULTRA_STARTED, EventKind.ULTRA_STOPPED, EventKind.ULTRA_NO_CAP_CHANGED}
)
"""The only kinds this store writes."""


class PostgresUltraControlStore:
    """Declared by `interfaces/ultra_control_store_interface.py`."""

    KINDS: ClassVar[frozenset[EventKind]] = ULTRA_CONTROL_KINDS
    """The kinds this store writes; `PostgresFailoverStore` names its own (ADR-0070)."""
    WHAT: ClassVar[str] = "an ULTRA control"

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

    async def record(
        self,
        project_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
        *,
        at: datetime,
    ) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"{kind.value} is not {self.WHAT}")
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(_LOCK_PROJECT, project_id)
            if row is None:
                raise UnknownProject(f"unknown project {project_id}")
            project = self._rows.to_record(row)
            if not isinstance(project.phase, Phase):
                raise WrongPhase(
                    f"project {project_id} is in phase {project.phase.value!r}, which this "
                    f"vibey does not know; it will not record {self.WHAT} there"
                )
            body = dict(payload)
            await self._appender.append(
                conn,
                LedgerEventDraft(
                    project_id=project_id,
                    cycle=project.cycle,
                    phase=project.phase,
                    kind=kind,
                    engine_id=None,
                    job_id=None,
                    causation_id=None,
                    correlation_id=self._correlation.for_project(project_id).value,
                    provenance=Provenance.TRUSTED,
                    produced_at=at,
                    payload=body,
                    digest=digest_event(body),
                ),
            )
