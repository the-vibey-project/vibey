# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres persistence for project lifecycle and guarded phase updates."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import ProjectRecord
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    PhaseTransitionedDraftBuilderInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft


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


class PhaseTransitionedDraftBuilder:
    """Turns a settled phase move into the `PhaseTransitioned` draft.

    The event is filed under the phase the project is now IN, with the cycle
    and `produced_at` the same UPDATE returned, so the row and the event are
    one consistent snapshot of the transaction that made both. The payload
    fields are the four handoff-protocol.md names for this kind.

    `produced_at` is database time, deliberately and not by omission. The
    alternative is the caller's Clock, which every other ledger writer uses,
    and it was rejected here: this event's whole claim is that it and the
    project row were written by one statement, and a clock reading taken
    outside the transaction would put the event's `produced_at` at odds with
    the `updated_at` the very same UPDATE wrote into the row it describes.
    The cost is real and is stated rather than hidden: the ledger now carries
    two time sources -- handler clocks for everything else, the database for
    this kind -- and nothing checks their skew. A caller that needs the two
    reconciled must reconcile them, and `transition` returns the settled
    record precisely so it can (see
    tests/infrastructure/db/test_design_interview_end_to_end.py, which pins
    this event's `produced_at` to that record instead of to its FixedClock).
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def build(self, settled: ProjectRecord, expected: Phase, guard: str | None) -> LedgerEventDraft:
        """Build the draft for one settled transition.

        `guard` is carried end to end -- port, interface and payload -- but no
        application call site passes one today, so every event this writes in
        production records `guard: null`. That is disclosed rather than tidied
        away, because on an append-only ledger the two readings of a null are
        not the same claim: "this move was made with no guard in force" and
        "guards are not wired up yet" are different facts, and only the second
        is true. The parameter stays because removing it would make the seam
        less configurable than it is (ADR-0018) and because the guard is the
        caller's to name, not this builder's to invent; what is missing is the
        call sites, and that is the work, not the signature.
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
            correlation_id=self._correlation.for_project(settled.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=settled.updated_at,
            payload=payload,
            digest=digest_event(payload),
        )


DEFAULT_TRANSITION_DRAFTS: Final[PhaseTransitionedDraftBuilderInterface] = (
    PhaseTransitionedDraftBuilder()
)


class PostgresProjectRepository:
    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        drafts: PhaseTransitionedDraftBuilderInterface = DEFAULT_TRANSITION_DRAFTS,
    ) -> None:
        self._pool = pool
        self._events = appender
        self._drafts = drafts

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
            await self._events.append(conn, self._drafts.build(settled, expected, guard))
            return settled
