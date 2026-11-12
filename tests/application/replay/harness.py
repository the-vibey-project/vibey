# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Delivering a job twice leaves the world as one delivery did (CLAUDE.md: "Every job is
idempotent under replay. Workers die; the lease expires and another worker picks it up").

A replay case builds a handler over persisted fakes (the ledger, the queue, whatever the
handler writes to), runs the job once, and captures a *content* snapshot of everything the
handler touched. A lease expiry is then simulated the way
``test_build_decompose_handler.py`` does it: a NEW handler instance over the SAME persisted
fakes, handed the SAME job. The second snapshot must equal the first, field by field. A count
would pass a handler that rewrites a row with different content, or swaps one event for
another; content does not (SP2-A Review Focus 1).

Helpers here are module functions and two value-type dataclasses; this is test support, not
production code, so ADR-0016's class rule does not apply.
"""

from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EngineEvent, JobRecord
from vibey.application.interfaces.queue import JobHandler, Outcome
from vibey.application.worker import Defer, Failure, Park, Success

Snapshot = Mapping[str, object]


@dataclass
class ReplayRig:
    """One case's world.

    ``handler`` is the instance that takes the first delivery; ``redeliver()`` builds the
    instance that takes the second, over the same persisted fakes (a worker died and another
    picked the job up: nothing but the persisted state survives). ``snapshot()`` reads that
    persisted state as comparable content. ``prepare`` is the setup that must have happened
    before the job could be delivered (a human answering a gate, say); it runs once, before
    the first delivery, and is not part of what is replayed.
    """

    handler: JobHandler
    job: JobRecord
    snapshot: Callable[[], Snapshot]
    redeliver: Callable[[], JobHandler]
    prepare: Callable[[], Awaitable[None]] | None = None


@dataclass(frozen=True)
class ReplayCase:
    """``kind`` names the handler module under ``src/vibey/application`` the case covers
    (``build_implement`` for ``build_implement_handler.py``); the census reads it."""

    name: str
    kind: str
    build: Callable[[], ReplayRig]


def event_content(event: EngineEvent) -> dict[str, object]:
    """An engine event as content. Nothing is dropped: ``at`` comes from the case's fixed
    clock, so it is a real field of the event, not a volatile one."""
    return {"kind": event.kind, "at": event.at, "payload": dict(event.payload)}


def job_row_content(job: JobRecord, dependencies: Sequence[object]) -> dict[str, object]:
    """A queue row as content: everything the row holds, including its id (an idempotent
    enqueue returns the SAME row, so a new id on replay is a duplicate), its dependencies,
    attempts and state. Only ``created_at`` and ``updated_at`` are left out: they are
    wall-clock stamps the fake takes from ``datetime.now`` and legitimately differ between
    two deliveries. ``run_after`` and ``lease_expires_at`` are kept."""
    row: dict[str, Any] = {
        field: getattr(job, field)
        for field in job.__dataclass_fields__
        if field not in {"created_at", "updated_at"}
    }
    row["dependencies"] = tuple(dependencies)
    return row


class ContentLedger:
    """A ``BuildLedger`` that keeps every argument of every ``record`` call, not just the
    event: which job wrote it, under which correlation and causation, as which engine."""

    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

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

    def content(self) -> dict[str, object]:
        """What a redelivery is held to, in two parts.

        ``own`` is what the handler records on its own account (no ``causation_id``): the
        DISTINCT entries, so a derived identity restated on a redelivery (the gate evidence
        ``integrate-gates-<item>``, the verify independence decision) is one fact said
        twice, while an entry whose CONTENT differs from every earlier one is a new fact and
        shows. ``runs`` is the kinds of the run-scoped events (``causation_id`` is the engine
        run): a redelivery really does run the engine again, so its events are new facts with
        new run ids and times (legitimately volatile); only the set of kinds is compared.
        """
        own: list[dict[str, object]] = []
        for entry in self.entries:
            if entry["causation_id"] is None and entry not in own:
                own.append(entry)
        runs = sorted({str(e["kind"]) for e in self.entries if e["causation_id"] is not None})
        return {"own": own, "runs": runs}


def jobs_content(jobs: FakeJobRepository) -> list[Mapping[str, object]]:
    """Every row the queue holds (adopted jobs are not rows), with its dependencies."""
    return sorted_rows(
        job_row_content(job, jobs.dependencies.get(job.id, ())) for job in jobs._jobs.values()
    )


def outcome_kind(outcome: Outcome) -> str:
    """The outcome's class. A replay may legitimately answer with a different RESULT (the
    decompose handler reports ``replayed: True`` once it finds the committed fan-out), but
    never with a different kind of outcome."""
    for cls in (Success, Failure, Park, Defer):
        if isinstance(outcome, cls):
            return cls.__name__
    raise AssertionError(f"unknown outcome {outcome!r}")


def sorted_rows(rows: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Rows in a stable order, so two snapshots compare by content and not by insertion."""
    return sorted(rows, key=lambda row: (str(row["kind"]), str(row["idempotency_key"])))


def _differences(first: Snapshot, second: Snapshot) -> list[str]:
    lines: list[str] = []
    for key in sorted(set(first) | set(second)):
        if first.get(key) != second.get(key):
            lines.append(f"  {key}:\n    once:  {first.get(key)!r}\n    twice: {second.get(key)!r}")
    return lines


async def assert_replay_is_idempotent(case: ReplayCase) -> None:
    """Deliver once, snapshot, simulate a lease expiry (a new handler over the same persisted
    state), deliver again, and demand the second snapshot equal the first."""
    rig = case.build()
    if rig.prepare is not None:
        await rig.prepare()

    first_outcome = await rig.handler.handle(rig.job)
    once = dict(rig.snapshot())

    second_outcome = await rig.redeliver().handle(rig.job)
    twice = dict(rig.snapshot())

    differences = _differences(once, twice)
    assert not differences, (
        f"{case.name}: a redelivery changed what one delivery left behind:\n"
        + "\n".join(differences)
    )
    assert outcome_kind(first_outcome) == outcome_kind(second_outcome), (
        f"{case.name}: the first delivery answered {first_outcome!r}, the second {second_outcome!r}"
    )


__all__ = [
    "ContentLedger",
    "ReplayCase",
    "ReplayRig",
    "assert_replay_is_idempotent",
    "event_content",
    "job_row_content",
    "jobs_content",
    "outcome_kind",
    "sorted_rows",
]
