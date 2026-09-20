# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres persistence for project lifecycle and guarded phase updates."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import ProjectRecord
from vibey.application.interfaces import NotificationSink
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import PHASE_PARSER, Phase, UnrecognizedPhase
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    PhaseTransitionedDraftBuilderInterface,
    ProjectRowMapperInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft

logger = logging.getLogger(__name__)


class ProjectRowMapper:
    """Turns one `project` row into a `ProjectRecord`, one way for every reader.

    `phase` is a Postgres enum a newer vibey widens with a migration, so it is read
    forward-compatibly (vibey#287): a phase this vibey does not know comes back as
    an `UnrecognizedPhase`, never a `ValueError`. Reading the project must never be
    what takes a worker down; deciding not to work on it is the caller's job, and
    the claim already refuses every job of such a project.
    """

    def __init__(
        self, phases: StoredValueParserInterface[Phase, UnrecognizedPhase] = PHASE_PARSER
    ) -> None:
        self._phases = phases

    def to_record(self, row: asyncpg.Record) -> ProjectRecord:
        return ProjectRecord(
            project_id=row["id"],
            name=row["name"],
            repo_path=Path(row["repo_path"]),
            phase=self._phases.parse(row["phase"]),
            cycle=row["cycle"],
            max_cycles=row["max_cycles"],
            config=json.loads(row["config"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


PROJECT_ROWS: Final[ProjectRowMapperInterface] = ProjectRowMapper()
"""The one row mapper every reader of `project` shares. Stateless, so one instance serves."""


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
        phase = settled.phase
        if not isinstance(phase, Phase):
            # The CAS only ever sets a phase its caller named, so this is a row that
            # changed under it. Writers stay strict (vibey#287): never ledger a
            # phase this vibey cannot vouch for.
            raise ValueError(
                f"project {settled.project_id} settled in phase {phase.value!r}, which "
                "this vibey does not know; it will not ledger a move into it"
            )
        payload: dict[str, object] = {
            "from": expected.value,
            "to": phase.value,
            "cycle": settled.cycle,
            "guard": guard,
        }
        return LedgerEventDraft(
            project_id=settled.project_id,
            cycle=settled.cycle,
            phase=phase,
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
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
        notifications: NotificationSink | None = None,
    ) -> None:
        self._pool = pool
        self._events = appender
        self._drafts = drafts
        self._rows = rows
        self._notifications = notifications

    @staticmethod
    def _notification_failed(result: Mapping[str, object], config: Mapping[str, object]) -> bool:
        if result.get("enabled") is not True:
            return False
        if result.get("error"):
            return True
        raw_config = config.get("notifications")
        desktop_enabled = (
            isinstance(raw_config, Mapping)
            and raw_config.get("enabled") is True
            and raw_config.get("desktop", True) is True
        )
        if desktop_enabled and result.get("desktop") is False:
            return True
        webhooks = result.get("webhooks")
        return isinstance(webhooks, list) and any(delivery is False for delivery in webhooks)

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
            return self._rows.to_record(row)

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM project WHERE id = $1", project_id)
            return self._rows.to_record(row) if row is not None else None

    async def get_latest(self) -> ProjectRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM project ORDER BY created_at DESC LIMIT 1")
            return self._rows.to_record(row) if row is not None else None

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
            settled = self._rows.to_record(row)
            await self._events.append(conn, self._drafts.build(settled, expected, guard))

        if self._notifications is not None:
            kind = "run_completed" if to is Phase.DONE else "phase_transitioned"
            title = "Run Completed" if to is Phase.DONE else "Phase Transitioned"
            message = (
                f"Project entered {to.value}"
                if to is not Phase.DONE
                else f"Project completed in cycle {settled.cycle}"
            )
            try:
                result = await self._notifications.notify(
                    project_id=settled.project_id,
                    kind=kind,
                    title=title,
                    message=message,
                    payload={
                        "from": expected.value,
                        "to": to.value,
                        "cycle": settled.cycle,
                    },
                    config=settled.config,
                )
                if self._notification_failed(result, settled.config):
                    logger.warning(
                        "notification delivery failed for project %s: %s",
                        settled.project_id,
                        result,
                    )
            except Exception as exc:  # noqa: BLE001 - delivery cannot undo a committed transition
                logger.warning(
                    "notification delivery raised for project %s: %s",
                    settled.project_id,
                    exc,
                )
        return settled
