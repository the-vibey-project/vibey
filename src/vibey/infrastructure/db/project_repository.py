# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres persistence for project lifecycle and guarded phase updates."""

import json
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

from vibey.application.dto import ProjectRecord
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import ConnectionEventAppender
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.interfaces import EventAppender


def _row_to_project(row: asyncpg.Record) -> ProjectRecord:
    return ProjectRecord(
        project_id=row["id"],
        name=row["name"],
        repo_path=Path(row["repo_path"]),
        phase=Phase(row["phase"]),
        cycle=row["cycle"],
        max_cycles=row["max_cycles"],
        config=json.loads(row["config"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresProjectRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._events: EventAppender = ConnectionEventAppender()

    async def create(
        self,
        name: str,
        repo_path: Path,
        *,
        max_cycles: int,
        config: Mapping[str, object],
    ) -> ProjectRecord:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO project (name, repo_path, max_cycles, config)
                VALUES ($1, $2, $3, $4::jsonb)
                RETURNING *
                """,
                name,
                str(repo_path.resolve()),
                max_cycles,
                json.dumps(dict(config)),
            )
            if row is None:
                raise LookupError("project insert returned no row")
            return _row_to_project(row)

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM project WHERE id = $1", project_id)
            return _row_to_project(row) if row is not None else None

    async def get_latest(self) -> ProjectRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM project ORDER BY created_at DESC LIMIT 1")
            return _row_to_project(row) if row is not None else None

    async def transition(
        self,
        project_id: UUID,
        *,
        expected: Phase,
        to: Phase,
        cycle: int | None = None,
        guard: str | None = None,
    ) -> ProjectRecord:
        """Compare-and-set the phase and ledger the move in ONE transaction.

        The six-phase model is the product and the ledger is its evidence, so
        every real move has to leave a `PhaseTransitioned` behind. Appending
        after the CAS had committed would lose the event whenever the worker
        died in between, and an append-only ledger has no way to put a lost
        event back where it belonged. Replay stays safe because the CAS is
        itself the guard: a second attempt finds the row already in `to`,
        raises, and rolls the whole transaction back, so no event is written
        twice and none is written without its transition.

        `guard` is the caller's name for the rule that permitted the move (the
        `reason` it handed `evaluate_transition`); it is recorded verbatim in
        the payload and defaults to None rather than to any phrase this layer
        invents on the caller's behalf.
        """
        async with self._pool.acquire() as conn, conn.transaction():
            if cycle is not None:
                row = await conn.fetchrow(
                    """
                    UPDATE project
                    SET phase = $3, cycle = $4, updated_at = now()
                    WHERE id = $1 AND phase = $2
                    RETURNING *
                    """,
                    project_id,
                    expected.value,
                    to.value,
                    cycle,
                )
            else:
                row = await conn.fetchrow(
                    """
                    UPDATE project
                    SET phase = $3, updated_at = now()
                    WHERE id = $1 AND phase = $2
                    RETURNING *
                    """,
                    project_id,
                    expected.value,
                    to.value,
                )
            if row is None:
                raise ValueError(
                    f"project {project_id} is not in expected phase {expected.value!r}"
                )
            settled = _row_to_project(row)
            await self._events.append(conn, _transition_draft(settled, expected, guard))
            return settled


def _transition_draft(
    settled: ProjectRecord, expected: Phase, guard: str | None
) -> LedgerEventDraft:
    """Builds the PhaseTransitioned draft for a move that has just landed.

    A module-level function rather than a method (ADR-0016) because it is a
    pure mapping from a settled row to a draft: it holds no state, touches no
    connection, and belongs to neither the repository's nor the appender's
    identity. The event is filed under the phase the project is now IN, with
    the cycle and `produced_at` the same UPDATE returned, so the row and the
    event are one consistent snapshot of the transaction that made both. The
    payload fields are the four handoff-protocol.md names for this kind.
    """
    payload: dict[str, object] = {
        "from": expected.value,
        "to": settled.phase.value,
        "cycle": settled.cycle,
        "guard": guard,
    }
    return LedgerEventDraft(
        project_id=settled.project_id,
        cycle=settled.cycle,
        phase=settled.phase,
        kind=EventKind.PHASE_TRANSITIONED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=settled.updated_at,
        payload=payload,
        digest=digest_event(payload),
    )
