# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""State machine: the in-memory ledger and PostgreSQL, driven by one random sequence.

``test_ledger_repository_contract.py`` pins the cases somebody thought of. This drives
``InMemoryLedgerRepository`` (the reference) and ``PostgresLedgerRepository`` (the
subject) through the SAME random sequence of ``append`` calls -- ordinary events,
decisions, and corrections that supersede an earlier decision -- and ``range``,
``latest_seq`` and ``all_for_project`` reads, and asserts that both returned the same
thing at every step and that both event tables read the same after it. So a fake that
drifts from the SQL in a sequence nobody wrote down still fails here.

Normalisation. ``event_id`` is minted on each side (``gen_random_uuid()``) and the
PostgreSQL projects are rows of their own, so an event is named by the position of the
append that returned it and a project by its index; everything else the machine chose
(the drafts are identical on both sides) is compared as it is, ``produced_at`` by its
ISO form so a zone the fake kept and the database would not shows.

The table. The machine reads each side's stored events past the repository -- the fake's
``_events``, PostgreSQL's ``event`` rows through the readers' own row mapper -- so a
wrong row behind right answers is still seen, and the laws below judge what is stored,
not what a reader chose to return.

Laws (checked on each side's table after every step; the source of each in brackets):
- seqs are 1..n in every project, each project counting on its own [``append_event``:
  the per-project ``event_seq`` counter];
- the hash chain verifies [``domain/ledger_chain.py`` ``LedgerChain.verify``: contiguous
  seqs, every digest the digest of its stored payload];
- every stored event is exactly the event ``append`` returned for it, however many
  corrections came after [CLAUDE.md: "The ledger is append-only. No updates, no
  deletes."; migrations 0016/0017];
- the open decisions are those no correction has superseded [CLAUDE.md: "Corrections
  are new events that supersede prior ones"; ``domain/ledger.py`` ``open_items``].

The negative controls run the same machine without a database and require Hypothesis to
find the fault: they are what shows the machine can fail. One wrong ledger per check. A
fault in what a reader returns runs as the reference against the correct fake, so only
that reader's comparison sees it; a fault in what is stored behind right answers does
too, so only the table comparison sees it; and a fault the same on both sides -- where
every comparison agrees -- runs as both, so only its law can object.
"""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, fields, replace
from datetime import UTC, datetime, timedelta, timezone
from itertools import count
from typing import Any, Protocol
from uuid import UUID, uuid4

import asyncpg
import pytest
from hypothesis import Phase as HypothesisPhase
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.fakes.ledger_repository import InMemoryLedgerRepository, LedgerRepository
from vibey.domain.engine import EngineId, StoredEngineId
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    LedgerEventKind,
    Provenance,
    StoredProvenance,
    canonical_bytes,
    digest_event,
    open_items,
)
from vibey.domain.ledger_chain import LedgerChain
from vibey.domain.phase import Phase, StoredPhase
from vibey.infrastructure.db.ledger_repository import EVENT_ROWS, PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft

WRITTEN = 2
"""Projects the machine appends to; one more, never written, is only ever read."""
PROJECTS = st.integers(min_value=0, max_value=WRITTEN - 1)
READ_PROJECTS = st.integers(min_value=0, max_value=WRITTEN)
SEQS = st.integers(min_value=-1, max_value=12)
BASE = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
ZONES = (UTC, timezone(timedelta(hours=5, minutes=30)), timezone(timedelta(hours=-8)))
SECRET = "sk-" + "B" * 20
"""Vendor-shaped (redact.py), so a payload carrying it is stored redacted."""
SCALARS = st.one_of(
    st.integers(min_value=-3, max_value=3),
    st.sampled_from(["", "a", "build", f"key {SECRET}"]),
    st.booleans(),
    st.none(),
)
PAYLOADS: st.SearchStrategy[dict[str, object]] = st.dictionaries(
    st.sampled_from(["n", "note", "path", "api_key"]),
    SCALARS | st.lists(SCALARS, max_size=2),
    max_size=3,
)
"""JSON a jsonb column hands back unchanged, with a sensitive key name and a vendor-shaped
secret often enough that redaction is exercised. Left out on purpose: what jsonb refuses
(U+0000, NaN, the infinities -- pinned on both sides by the contract) and the floats it
rewrites (``1e+16`` and up, ``-0.0``) -- a defect of the real repository, pinned there as a
strict xfail, that this machine would otherwise report on every run."""
ORDINARY = (EventKind.TURN_REQUESTED, EventKind.FILE_EDITED, EventKind.TOOL_INVOKED)
IDS = (None, UUID(int=1), UUID(int=2))
CORRELATIONS = (UUID(int=10), UUID(int=11))

MACHINE_SETTINGS = settings(max_examples=25, stateful_step_count=20, deadline=None)
CONTROL_SETTINGS = settings(
    max_examples=200,
    stateful_step_count=20,
    deadline=None,
    database=None,
    derandomize=True,
    phases=[HypothesisPhase.generate],
)
"""Deterministic (``derandomize``) and remembering nothing, so a control's verdict never
depends on an earlier run. Generation only: a control needs the first failure, not the
smallest, and its message is matched whatever the example (shrinking was most of its time,
the explain phase only annotates the report)."""


class Runner(Protocol):
    """Runs one coroutine to completion from the machine's (synchronous) thread."""

    def __call__[T](self, coro: Coroutine[Any, Any, T], /) -> T: ...


@dataclass(frozen=True)
class Side:
    """One repository under the machine, its projects (``WRITTEN`` written, then one
    never written), and ``stored``: the project's events as the table holds them, read
    past the repository and in seq order."""

    name: str
    repo: LedgerRepository
    projects: tuple[UUID, ...]
    stored: Callable[[UUID], Coroutine[Any, Any, tuple[LedgerEvent, ...]]]


type Sides = Callable[[], Coroutine[Any, Any, tuple[Side, Side]]]


@dataclass(frozen=True)
class Seen:
    """One event as both sides must agree on it: no generated id."""

    project: int | None
    seq: int
    event: int | None
    """The position of the append that returned this event on its side; None for an
    event no append returned."""
    cycle: int
    phase: StoredPhase
    kind: LedgerEventKind
    engine_id: StoredEngineId | None
    job_id: UUID | None
    causation_id: UUID | None
    correlation_id: UUID
    provenance: StoredProvenance
    produced_at: str
    payload: str
    """``canonical_bytes`` of the payload, so ``True``, ``1`` and ``1.0`` -- equal as
    Python values, different as stored JSON -- do not compare equal."""
    digest: str


NORMALISED_AS = {"event_id": "event", "project_id": "project"}
"""The two stored fields ``Seen`` names by position rather than by generated id."""


class FakeSides:
    @staticmethod
    def of(repo: InMemoryLedgerRepository, name: str = "fake") -> Side:
        async def stored(project_id: UUID) -> tuple[LedgerEvent, ...]:
            return tuple(sorted(repo._events.get(project_id, ()), key=lambda e: e.seq))

        projects = tuple(uuid4() for _ in range(WRITTEN + 1))
        repo.projects.update(projects[:WRITTEN])
        return Side(name, repo, projects, stored)


# -- wrong ledgers, for the negative controls ----------------------------------------------


class SeqReusingLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: the second event of a project reuses seq 1 (a counter read
    before it was advanced), so ``append`` answers a seq another event already holds."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        event = await super().append(draft)
        rows = self._events[draft.project_id]
        if event.seq == 2:
            rows[-1] = replace(rows[-1], seq=1)
            return self._copy(rows[-1])
        return event


class HalfOpenRangeLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: ``range`` leaves out ``to_seq`` (``seq < $3``, not ``BETWEEN``)."""

    async def range(
        self, project_id: UUID, *, from_seq: int, to_seq: int
    ) -> tuple[LedgerEvent, ...]:
        return await super().range(project_id, from_seq=from_seq, to_seq=to_seq - 1)


class TableWideLatestSeqLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: ``latest_seq`` forgets ``WHERE project_id = $1`` and answers the
    highest seq in the whole table."""

    async def latest_seq(self, project_id: UUID) -> int:
        return max((e.seq for rows in self._events.values() for e in rows), default=0)


class NewestFirstLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: ``all_for_project`` orders by ``seq DESC``."""

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(reversed(await super().all_for_project(project_id)))


class ForgedDigestLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: stores every event under a digest its payload does not produce,
    yet every reader answers with the right one. Every value it returns is right; only the
    table is wrong, so only the table comparison can see it."""

    FORGED = "0" * 64

    def __init__(self) -> None:
        super().__init__()
        self._true: dict[tuple[UUID, int], str] = {}

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        event = await super().append(draft)
        self._true[(event.project_id, event.seq)] = event.digest
        rows = self._events[draft.project_id]
        rows[-1] = replace(rows[-1], digest=self.FORGED)
        return event

    def _copy(self, event: LedgerEvent) -> LedgerEvent:
        digest = self._true.get((event.project_id, event.seq), event.digest)
        return super()._copy(replace(event, digest=digest))


class SharedCounterLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: one seq counter for the whole table instead of one per project,
    so a project's first event need not be seq 1."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        await super().append(draft)
        total = sum(len(rows) for rows in self._events.values())
        rows = self._events[draft.project_id]
        rows[-1] = replace(rows[-1], seq=total)
        return self._copy(rows[-1])


class DraftDigestLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: keeps the digest the caller took before redaction, so an event
    whose payload was redacted carries a digest its stored payload does not produce."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        await super().append(draft)
        rows = self._events[draft.project_id]
        rows[-1] = replace(rows[-1], digest=draft.digest)
        return self._copy(rows[-1])


class AmendingLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: a correction is also written into the decision it supersedes --
    ``superseded_by`` added to the original's payload, its digest recomputed so the chain
    still holds. An update in place, which the ledger forbids."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        event = await super().append(draft)
        superseded = draft.payload.get("supersedes")
        rows = self._events[draft.project_id]
        for at, old in enumerate(rows):
            if superseded is not None and old.payload.get("decision_id") == superseded:
                payload = {**old.payload, "superseded_by": draft.payload["decision_id"]}
                rows[at] = replace(old, payload=payload, digest=digest_event(payload))
        return event


class SupersedesDroppingLedger(InMemoryLedgerRepository):
    """WRONG ON PURPOSE: strips ``supersedes`` from every payload before storing it (an
    allow-list of payload keys that forgot one), so a correction no longer corrects."""

    async def append(self, draft: LedgerEventDraft) -> LedgerEvent:
        kept = {key: value for key, value in draft.payload.items() if key != "supersedes"}
        return await super().append(replace(draft, payload=kept, digest=digest_event(kept)))


# -- the machine -----------------------------------------------------------------------------


class LedgerRepositoryMachine(RuleBasedStateMachine):
    """The reference and the subject, driven in lockstep; see the module docstring."""

    def __init__(self, sides: Sides, run: Runner) -> None:
        super().__init__()
        self.run = run
        self.reference, self.subject = run(sides())
        self.positions = count()
        self.appended: tuple[dict[UUID, int], dict[UUID, int]] = ({}, {})
        self.returned: tuple[dict[UUID, LedgerEvent], dict[UUID, LedgerEvent]] = ({}, {})
        self.decisions: list[list[str]] = [[] for _ in range(WRITTEN)]
        self.superseded: list[set[str]] = [set() for _ in range(WRITTEN)]
        self.minted = count(1)

    # -- helpers ---------------------------------------------------------------------------

    @property
    def sides(self) -> tuple[Side, Side]:
        return (self.reference, self.subject)

    def _seen(self, side: int, event: LedgerEvent) -> Seen:
        projects = self.sides[side].projects
        return Seen(
            project=projects.index(event.project_id) if event.project_id in projects else None,
            seq=event.seq,
            event=self.appended[side].get(event.event_id),
            cycle=event.cycle,
            phase=event.phase,
            kind=event.kind,
            engine_id=event.engine_id,
            job_id=event.job_id,
            causation_id=event.causation_id,
            correlation_id=event.correlation_id,
            provenance=event.provenance,
            produced_at=event.produced_at.isoformat(),
            payload=canonical_bytes(event.payload).decode(),
            digest=event.digest,
        )

    def _append(self, project: int, template: LedgerEventDraft) -> None:
        """One draft, the same on both sides but for the project it names there."""
        made = [
            self.run(side.repo.append(replace(template, project_id=side.projects[project])))
            for side in self.sides
        ]
        position = next(self.positions)
        for n, event in enumerate(made):
            self.appended[n].setdefault(event.event_id, position)
            self.returned[n][event.event_id] = event
        seen = [self._seen(n, event) for n, event in enumerate(made)]
        assert seen[0] == seen[1], (
            f"append diverged in project {project}:\n"
            f"{self.reference.name}: {seen[0]}\n{self.subject.name}: {seen[1]}"
        )

    @staticmethod
    def _draft(
        payload: dict[str, object],
        *,
        kind: EventKind,
        phase: Phase = Phase.DESIGN,
        engine_id: EngineId | None = None,
        job_id: UUID | None = None,
        causation_id: UUID | None = None,
        correlation_id: UUID = CORRELATIONS[0],
        provenance: Provenance = Provenance.AGENT,
        produced_at: datetime = BASE,
    ) -> LedgerEventDraft:
        """A draft as a caller builds one: its digest taken over the payload it hands in,
        before the repository redacts anything. ``project_id`` is set per side."""
        return LedgerEventDraft(
            project_id=UUID(int=0),
            cycle=1,
            phase=phase,
            kind=kind,
            engine_id=engine_id,
            job_id=job_id,
            causation_id=causation_id,
            correlation_id=correlation_id,
            provenance=provenance,
            produced_at=produced_at,
            payload=payload,
            digest=digest_event(payload),
        )

    def _instant(self, zone: timezone) -> datetime:
        """A production instant no other append of this run uses, in ``zone``."""
        return (BASE + timedelta(microseconds=1001 * next(self.minted))).astimezone(zone)

    # -- rules -----------------------------------------------------------------------------

    @initialize(project=PROJECTS)
    def seed(self, project: int) -> None:
        """A decision in the ledger from the first step, so a correction has one to name."""
        self.decide(project)

    @rule(
        project=PROJECTS,
        kind=st.sampled_from(ORDINARY),
        phase=st.sampled_from(Phase),
        engine_id=st.none() | st.sampled_from(EngineId),
        job_id=st.sampled_from(IDS),
        causation_id=st.sampled_from(IDS),
        correlation_id=st.sampled_from(CORRELATIONS),
        provenance=st.sampled_from(Provenance),
        zone=st.sampled_from(ZONES),
        payload=PAYLOADS,
    )
    def append(
        self,
        project: int,
        kind: EventKind,
        phase: Phase,
        engine_id: EngineId | None,
        job_id: UUID | None,
        causation_id: UUID | None,
        correlation_id: UUID,
        provenance: Provenance,
        zone: timezone,
        payload: dict[str, object],
    ) -> None:
        self._append(
            project,
            self._draft(
                payload,
                kind=kind,
                phase=phase,
                engine_id=engine_id,
                job_id=job_id,
                causation_id=causation_id,
                correlation_id=correlation_id,
                provenance=provenance,
                produced_at=self._instant(zone),
            ),
        )

    @rule(project=PROJECTS)
    def decide(self, project: int) -> None:
        decision = f"d{next(self.minted)}"
        self.decisions[project].append(decision)
        self._append(
            project,
            self._draft(
                {"decision_id": decision, "text": "use PostgreSQL"},
                kind=EventKind.DECISION_RECORDED,
                produced_at=self._instant(UTC),
            ),
        )

    @rule(project=PROJECTS, pick=st.integers(min_value=0, max_value=100))
    def correct(self, project: int, pick: int) -> None:
        """A new decision naming an earlier one it supersedes -- never an edit of it."""
        if not self.decisions[project]:
            return
        old = self.decisions[project][pick % len(self.decisions[project])]
        decision = f"d{next(self.minted)}"
        self.decisions[project].append(decision)
        self.superseded[project].add(old)
        self._append(
            project,
            self._draft(
                {"decision_id": decision, "supersedes": old, "text": "use PostgreSQL 17"},
                kind=EventKind.DECISION_RECORDED,
                provenance=Provenance.TRUSTED,
                produced_at=self._instant(UTC),
            ),
        )

    @rule(project=READ_PROJECTS, low=SEQS, high=SEQS)
    def read_range(self, project: int, low: int, high: int) -> None:
        got = [
            [
                self._seen(n, event)
                for event in self.run(
                    side.repo.range(side.projects[project], from_seq=low, to_seq=high)
                )
            ]
            for n, side in enumerate(self.sides)
        ]
        assert got[0] == got[1], (
            f"range diverged for project {project}, seqs {low}..{high}:\n"
            f"{self.reference.name}: {got[0]}\n{self.subject.name}: {got[1]}"
        )

    @rule(project=READ_PROJECTS)
    def read_latest_seq(self, project: int) -> None:
        got = [self.run(side.repo.latest_seq(side.projects[project])) for side in self.sides]
        assert got[0] == got[1], (
            f"latest_seq diverged for project {project}: "
            f"{self.reference.name} {got[0]}, {self.subject.name} {got[1]}"
        )

    @rule(project=READ_PROJECTS)
    def read_all_for_project(self, project: int) -> None:
        got = [
            [
                self._seen(n, event)
                for event in self.run(side.repo.all_for_project(side.projects[project]))
            ]
            for n, side in enumerate(self.sides)
        ]
        assert got[0] == got[1], (
            f"all_for_project diverged for project {project}:\n"
            f"{self.reference.name}: {got[0]}\n{self.subject.name}: {got[1]}"
        )

    # -- invariants ------------------------------------------------------------------------

    @invariant()
    def both_tables_agree_and_keep_the_ledger_laws(self) -> None:
        tables = [
            [self.run(side.stored(project)) for project in side.projects] for side in self.sides
        ]
        seen = [
            [[self._seen(n, event) for event in events] for events in tables[n]] for n in (0, 1)
        ]
        assert seen[0] == seen[1], (
            f"ledgers diverged:\n{self.reference.name}: {seen[0]}\n{self.subject.name}: {seen[1]}"
        )
        for n, side in enumerate(self.sides):
            self._laws(n, side, tables[n])

    def _laws(self, n: int, side: Side, table: list[tuple[LedgerEvent, ...]]) -> None:
        for project, events in enumerate(table):
            seqs = [event.seq for event in events]
            assert seqs == list(range(1, len(events) + 1)), (
                f"{side.name}: project {project} holds seqs {seqs}, not 1..{len(events)}"
            )
            verified = LedgerChain().verify(side.projects[project], events)
            assert verified.ok, (
                f"{side.name}: project {project}'s chain does not verify: {verified.findings}"
            )
            for event in events:
                assert self.returned[n].get(event.event_id) == event, (
                    f"{side.name}: project {project} seq {event.seq} is not the event "
                    "append returned for it"
                )
            if project < WRITTEN:
                expected = tuple(
                    d for d in self.decisions[project] if d not in self.superseded[project]
                )
                found = open_items(events, EventKind.DECISION_RECORDED)
                assert found == expected, (
                    f"{side.name}: project {project}'s open decisions are {found}, not {expected}"
                )


class MachineHarness:
    """Runs the (synchronous) machine on a worker thread, every coroutine on this loop:
    the PostgreSQL pool belongs to the test's event loop. A pytest test rather than the
    machine's ``TestCase`` so it can take the database fixtures (see
    ``test_job_repository_machine.MachineHarness``)."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def __call__[T](self, coro: Coroutine[Any, Any, T], /) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def check(self, sides: Sides, config: settings) -> None:
        await asyncio.to_thread(
            run_state_machine_as_test,
            lambda: LedgerRepositoryMachine(sides, self),
            settings=config,
        )


def test_the_normalised_form_names_every_stored_field() -> None:
    # A field LedgerEvent gains must be compared too: Seen names each stored field, the
    # generated ids by position (NORMALISED_AS).
    stored = {NORMALISED_AS.get(f.name, f.name) for f in fields(LedgerEvent)}
    assert stored == {f.name for f in fields(Seen)}


# -- the fake against PostgreSQL ---------------------------------------------------------


async def test_the_fake_and_postgres_agree_through_random_operation_sequences(
    migrated_pool: asyncpg.Pool,
) -> None:
    # The ledger cannot be emptied between examples (it is append-only, 0016), so each
    # example writes to projects of its own.
    postgres = PostgresLedgerRepository(migrated_pool)

    async def stored(project_id: UUID) -> tuple[LedgerEvent, ...]:
        rows = await migrated_pool.fetch(
            "SELECT * FROM event WHERE project_id = $1 ORDER BY seq", project_id
        )
        return tuple(EVENT_ROWS.to_event(row) for row in rows)

    async def project() -> UUID:
        name = f"ledger-machine-{uuid4()}"
        pid = await migrated_pool.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            name,
            f"/tmp/{name}",
        )
        return UUID(str(pid))

    async def sides() -> tuple[Side, Side]:
        written = [await project() for _ in range(WRITTEN)]
        real = Side("postgres", postgres, (*written, uuid4()), stored)
        return FakeSides.of(InMemoryLedgerRepository()), real

    await MachineHarness(asyncio.get_running_loop()).check(sides, MACHINE_SETTINGS)


# -- controls, without a database ----------------------------------------------------------


def pair(
    reference: type[InMemoryLedgerRepository], subject: type[InMemoryLedgerRepository]
) -> Sides:
    """Fresh ledgers for every example: a fake's reset is a new instance."""

    async def sides() -> tuple[Side, Side]:
        return FakeSides.of(reference(), "wrong"), FakeSides.of(subject())

    return sides


async def test_the_machine_passes_the_fake_against_itself() -> None:
    # Positive control: two correct ledgers never diverge, so a failure below is the bug's.
    async def sides() -> tuple[Side, Side]:
        return (
            FakeSides.of(InMemoryLedgerRepository(), "fake-a"),
            FakeSides.of(InMemoryLedgerRepository()),
        )

    await MachineHarness(asyncio.get_running_loop()).check(sides, CONTROL_SETTINGS)


@pytest.mark.parametrize(
    ("wrong", "found"),
    [
        (SeqReusingLedger, r"^append diverged"),
        (HalfOpenRangeLedger, r"^range diverged"),
        (TableWideLatestSeqLedger, r"^latest_seq diverged"),
        (NewestFirstLedger, r"^all_for_project diverged"),
        # Right answers, wrong table: only the table comparison can find this one.
        (ForgedDigestLedger, r"^ledgers diverged"),
    ],
)
async def test_the_machine_finds_a_wrong_reference(
    wrong: type[InMemoryLedgerRepository], found: str
) -> None:
    # Negative control: the same machine over a deliberately wrong reference, against
    # the correct fake, must find the divergence -- and in that comparison.
    sides = pair(wrong, InMemoryLedgerRepository)
    with pytest.raises(AssertionError, match=found):
        await MachineHarness(asyncio.get_running_loop()).check(sides, CONTROL_SETTINGS)


@pytest.mark.parametrize(
    ("wrong", "found"),
    [
        (SharedCounterLedger, r"^wrong: project \d holds seqs"),
        (DraftDigestLedger, r"^wrong: project \d's chain does not verify"),
        (AmendingLedger, r"^wrong: project \d seq \d+ is not the event append returned"),
        (SupersedesDroppingLedger, r"^wrong: project \d's open decisions"),
    ],
)
async def test_the_machine_finds_a_law_both_sides_break(
    wrong: type[InMemoryLedgerRepository], found: str
) -> None:
    # Negative control: the same wrong ledger on BOTH sides, so every comparison agrees
    # and only the law can object; the reference's name is checked first.
    sides = pair(wrong, wrong)
    with pytest.raises(AssertionError, match=found):
        await MachineHarness(asyncio.get_running_loop()).check(sides, CONTROL_SETTINGS)
