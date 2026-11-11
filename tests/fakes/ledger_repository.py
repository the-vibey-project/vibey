# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An in-memory ledger that behaves like ``PostgresLedgerRepository``.

Held to the real repository by ``tests/contracts/test_ledger_repository_contract.py``
(cases somebody thought of) and ``test_ledger_repository_machine.py`` (random operation
sequences), so a test that stands on it stands on the SQL's behaviour, not on a guess.
Each behaviour below names the line of ``infrastructure/db/ledger_repository.py`` or
of the migrations it copies.

What it does not model, on purpose (none of it is reachable through a correct caller):

- the ``project`` foreign key: ``event.project_id`` references ``project(id)``, so
  PostgreSQL refuses an append to a project that does not exist; this keeps no project
  table and takes any id;
- jsonb's refusals and rewrites: a ``\\u0000`` in a string, or a NaN or infinite float,
  is refused by PostgreSQL and kept here; a float written with an exponent (``1e20``)
  comes back from jsonb as an integer and here as the float (equal, not the same type);
- concurrency: ``append_event`` serialises appends to one project on the ``event_seq``
  row; this is single-threaded.
"""

import json
from dataclasses import replace
from datetime import UTC
from typing import Protocol
from uuid import UUID, uuid4

from vibey.domain.ledger import LedgerEvent, digest_event
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.ledger.redact import redact_payload


class LedgerRepository(Protocol):
    """The precise shape ``PostgresLedgerRepository`` has. Its declared interface
    (``class_contracts.py`` ``PostgresLedgerRepositoryInterface``) states the same four
    methods over ``object``; this names the types the tests rely on."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent: ...

    async def range(
        self, project_id: UUID, *, from_seq: int, to_seq: int
    ) -> tuple[LedgerEvent, ...]: ...

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]: ...

    async def latest_seq(self, project_id: UUID) -> int: ...


class InMemoryLedgerRepository:
    """Per-project, append-only lists of events. ``_events`` is the table: the machine
    reads it directly, the way it reads PostgreSQL's ``event`` rows."""

    def __init__(self) -> None:
        self._events: dict[UUID, list[LedgerEvent]] = {}

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        # ConnectionEventAppender.append: redact, then digest what will be stored --
        # never the draft's own digest, which was taken before redaction.
        payload = redact_payload(draft.payload)
        digest = digest_event(payload)
        # `json.dumps(redacted_payload)` is an argument to the append_event call, so a
        # payload JSON cannot carry raises before any seq is claimed.
        stored = json.dumps(payload)
        rows = self._events.setdefault(draft.project_id, [])
        event = LedgerEvent(
            # 0002: `event_id uuid ... DEFAULT gen_random_uuid()`.
            event_id=uuid4(),
            project_id=draft.project_id,
            cycle=draft.cycle,
            phase=draft.phase,
            # append_event: the per-project `event_seq` counter, 1 first, one per append.
            # A failed append rolls the counter back with its transaction and no event
            # is ever removed, so the counter is always the number of events plus one.
            seq=len(rows) + 1,
            kind=draft.kind,
            engine_id=draft.engine_id,
            job_id=draft.job_id,
            causation_id=draft.causation_id,
            correlation_id=draft.correlation_id,
            provenance=draft.provenance,
            # 0009: the draft's instant, not insertion time. asyncpg binds a naive
            # datetime as the host's local time and returns timestamptz in UTC, which is
            # what `astimezone(UTC)` does to either kind of datetime.
            produced_at=draft.produced_at.astimezone(UTC),
            # The jsonb column hands back `json.loads` of what was stored.
            payload=json.loads(stored),
            digest=digest,
        )
        rows.append(event)
        # append reads the row back; the caller gets a copy, never the stored event.
        return self._copy(event)

    async def range(
        self, project_id: UUID, *, from_seq: int, to_seq: int
    ) -> tuple[LedgerEvent, ...]:
        # `WHERE project_id = $1 AND seq BETWEEN $2 AND $3 ORDER BY seq`.
        return tuple(
            self._copy(event)
            for event in self._ordered(project_id)
            if from_seq <= event.seq <= to_seq
        )

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        # `WHERE project_id = $1 ORDER BY seq`.
        return tuple(self._copy(event) for event in self._ordered(project_id))

    async def latest_seq(self, project_id: UUID) -> int:
        # `max(seq)`, read as 0 when the project has no events.
        return max((event.seq for event in self._events.get(project_id, ())), default=0)

    def _ordered(self, project_id: UUID) -> list[LedgerEvent]:
        return sorted(self._events.get(project_id, ()), key=lambda event: event.seq)

    def _copy(self, event: LedgerEvent) -> LedgerEvent:
        """A fresh event, as every SELECT builds one from the row: a caller that changes
        a payload it was handed changes nothing stored."""
        return replace(event, payload=json.loads(json.dumps(event.payload)))
