# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pairing and revocation, written to the ledger (ADR-0068).

A pairing is host-wide: a paired device may read every project its scopes cover. So each
`HubDevicePaired` and `HubDeviceRevoked` is appended to every project's ledger, in one
transaction, so each project's own history says which devices could reach it and from
when. The payload names the device, the name it gave, its scopes and who acted; never
its key. Filed like `BudgetCapChanged`: under the project's cycle and phase, no engine,
no job, `trusted` -- the host did it, through vibey's own hub.

A project in a phase this vibey does not know refuses the write, and the transaction
rolls back: writers stay strict (vibey#287), so a pairing is never recorded in some
projects and silently missing from others.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Final

import asyncpg

from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import WrongPhase
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import EventAppenderInterface, ProjectRowMapperInterface
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_PROJECTS: Final = "SELECT * FROM project ORDER BY id FOR KEY SHARE"


class PostgresPairingLedger:
    """Appends one pairing event to every project's ledger, atomically.

    Declared by `interfaces/pairing_interface.py::PairingLedgerInterface`."""

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

    async def record(self, kind: EventKind, payload: Mapping[str, object], at: datetime) -> int:
        """Appends `kind` with `payload` to every project; the number of projects written."""
        body = dict(payload)
        written = 0
        async with self._pool.acquire() as conn, conn.transaction():
            for row in await conn.fetch(_PROJECTS):
                project = self._rows.to_record(row)
                if not isinstance(project.phase, Phase):
                    raise WrongPhase(
                        f"project {project.project_id} is in phase {project.phase.value!r}, "
                        "which this vibey does not know; it will not record a pairing there"
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
