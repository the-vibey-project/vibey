# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Delivering a job twice leaves the world as one delivery did (CLAUDE.md: "Every job is
idempotent under replay. Workers die; the lease expires and another worker picks it up").

A replay case builds a handler over persisted fakes (the ledger, the queue, whatever the
handler writes to) and a job that sits READY in the faithful ``FakeJobRepository``. The harness
leases it (``attempts`` becomes 1), delivers it, and captures a *content* snapshot of
everything the handler touched. A lease expiry is then simulated as the queue does it: the
lease lapses, ``reap`` requeues the row, the lease is taken again (``attempts`` becomes 2, and
the handlers that branch on ``job.attempts`` see it), and a NEW handler instance over the SAME
persisted fakes gets the REFRESHED row (``test_build_decompose_handler.py`` simulates a
redelivery the same way). The second snapshot must equal the first, field by field. A count
would pass a handler that rewrites a row with different content; content does not (SP2-A
Review Focus 1).

Helpers here are module functions and two value-type dataclasses; this is test support, not
production code, so ADR-0016's class rule does not apply.
"""

from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EngineEvent, JobRecord
from vibey.application.interfaces.queue import JobHandler, Outcome
from vibey.application.worker import Defer, Failure, Park, Success

Snapshot = Mapping[str, object]

LEASE = timedelta(minutes=5)

RESULT_KEYS_A_REDELIVERY_MAY_CHANGE = frozenset({"replayed", "run_id"})
"""Keys of a Success result that legitimately differ on a redelivery: ``replayed`` is the
decompose handler saying it found the committed fan-out, ``run_id`` is the id of the engine
session a redelivery runs again."""


@dataclass
class ReplayRig:
    """One case's world.

    ``jobs`` holds ``job`` READY; the harness leases it. ``handler`` takes the first delivery;
    ``redeliver()`` builds the instance that takes the second, over the same persisted fakes (a
    worker died and another picked the job up: only persisted state survives). ``snapshot()``
    reads that persisted state as comparable content and is called once after each delivery.
    ``prepare`` is setup that must precede the delivery (a human answering a gate); it runs
    once, before the first lease, and is not part of what is replayed.
    """

    handler: JobHandler
    job: JobRecord
    jobs: FakeJobRepository
    snapshot: Callable[[], Snapshot]
    redeliver: Callable[[], JobHandler]
    prepare: Callable[[], Awaitable[None]] | None = None


@dataclass(frozen=True)
class ReplayCase:
    """``kind`` names the handler module under ``src/vibey/application`` the case covers
    (``build_implement`` for ``build_implement_handler.py``); the census reads it. ``build``
    gets a scratch directory the case's fakes may write under."""

    name: str
    kind: str
    build: Callable[[Path], ReplayRig]


def event_content(event: EngineEvent) -> dict[str, object]:
    """An engine event as content. Nothing is dropped: ``at`` comes from the case's fixed
    clock, so it is a real field of the event, not a volatile one."""
    return {"kind": event.kind, "at": event.at, "payload": dict(event.payload)}


# What a redelivery leaves unchanged in the delivered job's OWN row: what the job IS, not where
# it is in its lease (attempts, state, owner, expiry, run_after and the stamps all legitimately
# move when a lease lapses and is retaken).
_IDENTITY_FIELDS = (
    "id",
    "project_id",
    "cycle",
    "phase",
    "kind",
    "priority",
    "work_item_id",
    "payload",
    "requirement",
    "idempotency_key",
    "max_attempts",
)


def jobs_content(jobs: FakeJobRepository, delivered: UUID) -> list[Mapping[str, object]]:
    """Every row the queue holds, with its dependencies, in a stable order. Rows the handler
    enqueued are compared in full (an idempotent enqueue returns the SAME row, so a new id or
    a changed field is a duplicate or a rewrite); only ``created_at`` and ``updated_at``,
    wall-clock stamps from ``datetime.now`` in the fake, are left out. The delivered job's
    own row is compared through ``_IDENTITY_FIELDS`` only."""
    rows: list[Mapping[str, object]] = []
    for job, dependencies in jobs.rows():
        if job.id == delivered:
            row: dict[str, Any] = {field: getattr(job, field) for field in _IDENTITY_FIELDS}
        else:
            row = {
                field: getattr(job, field)
                for field in job.__dataclass_fields__
                if field not in {"created_at", "updated_at"}
            }
        row["dependencies"] = tuple(dependencies)
        rows.append(row)
    return sorted(rows, key=lambda row: (str(row["kind"]), str(row["idempotency_key"])))


class ContentLedger:
    """A ``BuildLedger`` that keeps every argument of every ``record`` call, split by delivery.

    ``after_delivery()`` closes one delivery's batch and returns what a redelivery is held
    to. The first delivery's batch is the reference:

    - ``own`` (no ``causation_id``: what the handler records on its own account) is the
      MULTISET of its entries, so a handler writing one entry twice in a single delivery shows.
    - ``runs`` is the engine-run events in order, with the run id and the time removed (the
      run id also appears in payload text, and a redelivery really does run the engine again,
      so a new id and new times are legitimate) and everything else kept.
    - ``unmatched`` is what a LATER batch adds that the first does not account for: an own
      entry that is new, different, or more frequent than in the first batch, or a run whose
      content differs from the first's. It is empty in the first snapshot.

    What a later batch is allowed: the same own entries again, and the same run events again.
    That is the ledger's restatement on a redelivery, not idempotence: the ledger is
    append-only and does not dedupe on identity (an entry such as ``integrate-gates-<item>``
    is written twice, identically), and the engine runs again. See #1887; tighten to exact
    entries once the ledger dedupes on identity, and delete the allowance here.
    """

    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []
        self._batches: list[list[dict[str, object]]] = []
        self._closed = 0

    async def record(  # type: ignore[no-untyped-def]
        self, *, project_id, cycle, job_id, engine_id, correlation_id, event, causation_id=None
    ):
        self.entries.append(
            {
                "project_id": project_id,
                "cycle": cycle,
                "job_id": job_id,
                "engine_id": engine_id,
                "correlation_id": correlation_id,
                "causation_id": causation_id,
                **event_content(event),
            }
        )

    @staticmethod
    def _run_content(entry: Mapping[str, object]) -> str:
        """A run-scoped entry without its run id (everywhere it appears) and its time."""
        run = str(entry["causation_id"])
        kept = {k: v for k, v in entry.items() if k not in {"causation_id", "at"}}
        return repr(kept).replace(run, "<run>")

    def after_delivery(self) -> dict[str, object]:
        self._batches.append(self.entries[self._closed :])
        self._closed = len(self.entries)
        first, later = self._batches[0], self._batches[1:]

        def own(batch: list[dict[str, object]]) -> Counter[str]:
            return Counter(repr(e) for e in batch if e["causation_id"] is None)

        def runs(batch: list[dict[str, object]]) -> list[str]:
            return [self._run_content(e) for e in batch if e["causation_id"] is not None]

        reference = own(first)
        unmatched: list[str] = []
        for batch in later:
            unmatched += sorted((own(batch) - reference).elements())
            if runs(batch) != runs(first):
                unmatched += runs(batch)
        return {
            "own": sorted(reference.items()),
            "runs": runs(first),
            "unmatched": unmatched,
        }


def outcome_content(outcome: Outcome) -> object:
    """The outcome as comparable content: its class, and for a Success its result without
    the keys a redelivery may legitimately change (``RESULT_KEYS_A_REDELIVERY_MAY_CHANGE``).
    Any other outcome is compared whole."""
    if isinstance(outcome, Success):
        kept = {
            key: value
            for key, value in outcome.result.items()
            if key not in RESULT_KEYS_A_REDELIVERY_MAY_CHANGE
        }
        return ("Success", kept)
    if isinstance(outcome, Failure | Park | Defer):
        return (type(outcome).__name__, outcome)
    raise AssertionError(f"unknown outcome {outcome!r}")


def _is_empty(value: object) -> bool:
    if isinstance(value, Mapping):
        return all(_is_empty(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return all(_is_empty(item) for item in value)
    return not value


def _differences(first: Snapshot, second: Snapshot) -> list[str]:
    lines: list[str] = []
    for key in sorted(set(first) | set(second)):
        if first.get(key) != second.get(key):
            lines.append(f"  {key}:\n    once:  {first.get(key)!r}\n    twice: {second.get(key)!r}")
    return lines


async def _lease(jobs: FakeJobRepository, job: JobRecord, owner: str) -> JobRecord:
    return jobs.lease(job.id, owner=owner, lease=LEASE)


async def assert_replay_is_idempotent(case: ReplayCase, scratch: Path) -> None:
    """Lease and deliver, snapshot, let the lease lapse and be retaken (a new handler over the
    same persisted state, the refreshed row), deliver again, and demand equal snapshots."""
    rig = case.build(scratch)
    if rig.prepare is not None:
        await rig.prepare()

    first_job = await _lease(rig.jobs, rig.job, "worker-1")
    assert first_job.attempts == 1, "the first delivery is the job's first attempt"
    first_outcome = await rig.handler.handle(first_job)
    once = dict(rig.snapshot())
    assert not _is_empty(once), f"{case.name}: the first delivery left nothing to compare"

    rig.jobs.expire_lease(rig.job.id)
    assert await rig.jobs.reap() == 1, "the lapsed lease is requeued"
    rig.jobs.make_all_due()
    second_job = await _lease(rig.jobs, rig.job, "worker-2")
    assert second_job.attempts == 2, "a redelivery arrives with the attempt counted"
    second_outcome = await rig.redeliver().handle(second_job)
    twice = dict(rig.snapshot())

    differences = _differences(once, twice)
    assert not differences, (
        f"{case.name}: a redelivery changed what one delivery left behind:\n"
        + "\n".join(differences)
    )
    assert outcome_content(first_outcome) == outcome_content(second_outcome), (
        f"{case.name}: the first delivery answered {first_outcome!r}, the second {second_outcome!r}"
    )


__all__ = [
    "ContentLedger",
    "ReplayCase",
    "ReplayRig",
    "assert_replay_is_idempotent",
    "event_content",
    "jobs_content",
    "outcome_content",
]
