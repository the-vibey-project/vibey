# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An in-memory ledger that behaves like ``PostgresLedgerRepository``.

Held to the real repository by ``tests/contracts/test_ledger_repository_contract.py``
(cases somebody thought of) and ``test_ledger_repository_machine.py`` (random operation
sequences), so a test that stands on it stands on the SQL's behaviour, not on a guess.
Each behaviour below names the line of ``infrastructure/db/ledger_repository.py`` or
of the migrations it copies.

What it refuses, as PostgreSQL does (each pinned by a contract case on both sides, with
the same asyncpg exception and SQLSTATE, probed against PostgreSQL 2026-11-11):

- a project that is not in ``projects`` (the ``project`` table): ``event_seq.project_id
  REFERENCES project(id)`` (0002), ``ForeignKeyViolationError``;
- U+0000 anywhere in a key or string: jsonb cannot hold it (``text`` cannot),
  ``UntranslatableCharacterError``;
- NaN and the infinities, which ``json.dumps`` writes as tokens JSON does not have:
  ``InvalidTextRepresentationError``.

What it does not model, on purpose:

- jsonb's number rewrites: a float Python renders with an exponent (``1e+16``, every
  float of magnitude 1e16 and up) comes back from jsonb as an integer, and ``-0.0`` as
  ``0.0``. The repository digests Python's rendering first, so on PostgreSQL such an
  event's stored digest is not its stored payload's and the hash chain reports
  ``digest_mismatch`` -- a defect of the real repository, pinned as a strict xfail in
  the contract, not one to copy here;
- concurrency: ``append_event`` serialises appends to one project on the ``event_seq``
  row; this is single-threaded.
"""

import json
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC
from typing import Protocol
from uuid import UUID, uuid4

import asyncpg

from vibey.domain.ledger import LedgerEvent, digest_event
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.ledger.redact import redact_payload

_NON_FINITE = object()
"""Stands in, while a payload is checked, for a NaN or infinity ``json.dumps`` wrote."""


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
    """Per-project, append-only lists of events. ``_events`` is the event table: the
    machine reads it directly, the way it reads PostgreSQL's ``event`` rows. ``projects``
    is the project table: a test adds the projects it writes to, as it would insert a
    ``project`` row."""

    def __init__(self, projects: Iterable[UUID] = ()) -> None:
        self.projects: set[UUID] = set(projects)
        self._events: dict[UUID, list[LedgerEvent]] = {}

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        # ConnectionEventAppender.append: redact, then digest what will be stored --
        # never the draft's own digest, which was taken before redaction.
        payload = redact_payload(draft.payload)
        digest = digest_event(payload)
        # `json.dumps(redacted_payload)` is an argument to the append_event call, so a
        # payload JSON cannot carry raises before any seq is claimed.
        stored = json.dumps(payload)
        # PostgreSQL then casts the argument (`$11::jsonb`) before append_event's body
        # runs, so jsonb's refusals come before the foreign key's; none claims a seq.
        self._as_jsonb(stored)
        if draft.project_id not in self.projects:
            raise asyncpg.ForeignKeyViolationError(
                'insert or update on table "event_seq" violates foreign key constraint '
                '"event_seq_project_id_fkey"'
            )
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

    @classmethod
    def _as_jsonb(cls, text: str) -> None:
        """Refuses what the jsonb cast refuses -- a NaN or infinite number, a U+0000 -- and,
        when a payload holds both, the one met first in document order, as PostgreSQL's
        lexer does (psql 2026-11-11: `{"a":"\\u0000","b":NaN}` is refused for the escape,
        `{"b":NaN,"a":"\\u0000"}` for the token)."""
        cls._refuse(json.loads(text, parse_constant=lambda token: _NON_FINITE))

    @classmethod
    def _refuse(cls, value: object) -> None:
        if value is _NON_FINITE:
            raise asyncpg.InvalidTextRepresentationError("invalid input syntax for type json")
        if isinstance(value, str) and "\x00" in value:
            raise asyncpg.UntranslatableCharacterError("unsupported Unicode escape sequence")
        if isinstance(value, dict):
            for key, item in value.items():
                cls._refuse(key)
                cls._refuse(item)
        if isinstance(value, list):
            for item in value:
                cls._refuse(item)

    def _ordered(self, project_id: UUID) -> list[LedgerEvent]:
        return sorted(self._events.get(project_id, ()), key=lambda event: event.seq)

    def _copy(self, event: LedgerEvent) -> LedgerEvent:
        """A fresh event, as every SELECT builds one from the row: a caller that changes
        a payload it was handed changes nothing stored."""
        return replace(event, payload=json.loads(json.dumps(event.payload)))
