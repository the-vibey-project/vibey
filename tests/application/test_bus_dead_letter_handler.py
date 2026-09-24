# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A parked dead letter, settled by a person's answer (ADR-0056)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository
from vibey.application.bus_dead_letter_handler import (
    BUS_DEAD_LETTER_GATE,
    BUS_DEAD_LETTER_GATE_KIND,
    BUS_DEAD_LETTER_KIND,
    DISMISS,
    REPLAY,
    BusDeadLetterHandler,
)
from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces import (
    BusDeadLetterGateInterface,
    BusDeadLetterHandlerInterface,
)
from vibey.application.interfaces.queue import Park, Success
from vibey.domain.job import JobState
from vibey.domain.phase import Phase

PROJECT = UUID("6f1c2a4e-0000-4000-8000-000000000000")


@dataclass
class RecordingBus:
    published: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        return None

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        self.published.append((queue, payload))

    async def consume(self, queue: str) -> dict[str, object] | None:
        return None


def _payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "queue": "vibey.jobs.dlq",
        "origin_queue": "vibey.jobs",
        "reason": "rejected",
        "identity": "id:m1",
        "first_death_at": "1",
        "truncated": False,
        "payload": {"job_id": "x"},
    }
    values.update(overrides)
    return values


def _job(payload: dict[str, object]) -> JobRecord:
    now = datetime(2026, 9, 24, tzinfo=UTC)
    return JobRecord(
        id=uuid4(),
        project_id=PROJECT,
        cycle=1,
        phase=Phase.BUILD,
        kind=BUS_DEAD_LETTER_KIND,
        state=JobState.LEASED,
        priority=0,
        work_item_id=None,
        payload=payload,
        requirement={},
        idempotency_key="bus.dead_letter:x",
        attempts=1,
        max_attempts=7,
        run_after=now,
        lease_owner="w",
        lease_expires_at=now,
        assigned_engine=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


async def _answered(gates: FakeHumanGateRepository, job: JobRecord, choice: object) -> None:
    gate = await gates.raise_gate(PROJECT, job.id, HumanGateRequest(kind="k", prompt="p"))
    await gates.answer(gate.gate_id, answer={"choice": choice}, answered_by="operator")


def test_the_handler_and_gate_satisfy_their_seams() -> None:
    handler = BusDeadLetterHandler(gates=FakeHumanGateRepository(), bus=RecordingBus())
    assert isinstance(handler, BusDeadLetterHandlerInterface)
    assert isinstance(BUS_DEAD_LETTER_GATE, BusDeadLetterGateInterface)


def test_the_gate_offers_replay_only_for_a_whole_json_object() -> None:
    request = BUS_DEAD_LETTER_GATE.request(_payload())
    assert request.kind == BUS_DEAD_LETTER_GATE_KIND
    assert request.options == (REPLAY, DISMISS)
    assert "publishes it back to 'vibey.jobs'" in request.prompt
    assert "(reason: 'rejected')" in request.prompt
    truncated = BUS_DEAD_LETTER_GATE.request(_payload(truncated=True))
    assert truncated.options == (DISMISS,)
    assert "cannot be replayed" in truncated.prompt
    assert BUS_DEAD_LETTER_GATE.request(_payload(payload=None)).options == (DISMISS,)


def test_the_gate_quotes_and_cuts_what_the_message_said() -> None:
    """Header values are the publisher's words: shown quoted and short, never as prose."""
    request = BUS_DEAD_LETTER_GATE.request(
        _payload(reason="ignore the above and " + "x" * 500), note="Lead."
    )
    assert request.prompt.startswith("Lead. ")
    assert "'ignore the above and " in request.prompt
    assert "x" * 201 not in request.prompt


async def test_dismiss_settles_it_and_sends_nothing() -> None:
    gates, bus = FakeHumanGateRepository(), RecordingBus()
    job = _job(_payload())
    await _answered(gates, job, " Dismiss ")
    outcome = await BusDeadLetterHandler(gates=gates, bus=bus).handle(job)
    assert outcome == Success({"dismissed": "id:m1"})
    assert bus.published == []


async def test_replay_publishes_it_back_to_where_it_died() -> None:
    gates, bus = FakeHumanGateRepository(), RecordingBus()
    job = _job(_payload())
    await _answered(gates, job, REPLAY)
    outcome = await BusDeadLetterHandler(gates=gates, bus=bus).handle(job)
    assert outcome == Success({"replayed": "id:m1", "to": "vibey.jobs"})
    assert bus.published == [("vibey.jobs", {"job_id": "x"})]


@pytest.mark.parametrize(
    "payload",
    [
        _payload(truncated=True),
        _payload(payload=None),
        _payload(origin_queue=""),
        _payload(origin_queue=3),
    ],
)
async def test_a_replay_that_cannot_be_made_raises_the_gate_again(
    payload: dict[str, object],
) -> None:
    gates, bus = FakeHumanGateRepository(), RecordingBus()
    job = _job(payload)
    await _answered(gates, job, REPLAY)
    outcome = await BusDeadLetterHandler(gates=gates, bus=bus).handle(job)
    assert isinstance(outcome, Park)
    assert outcome.request.prompt.startswith("That dead letter cannot be replayed.")
    assert bus.published == []


@pytest.mark.parametrize("choice", [None, "later", 3])
async def test_anything_else_raises_the_gate_again(choice: object) -> None:
    gates, bus = FakeHumanGateRepository(), RecordingBus()
    job = _job(_payload())
    if choice is not None:
        await _answered(gates, job, choice)
    outcome = await BusDeadLetterHandler(gates=gates, bus=bus).handle(job)
    assert isinstance(outcome, Park)
    assert outcome.request.prompt.startswith("Answer --choice replay or --choice dismiss.")


async def test_an_unanswered_gate_is_no_answer() -> None:
    gates, bus = FakeHumanGateRepository(), RecordingBus()
    job = _job(_payload())
    await gates.raise_gate(PROJECT, job.id, HumanGateRequest(kind="k", prompt="p"))
    outcome = await BusDeadLetterHandler(gates=gates, bus=bus).handle(job)
    assert isinstance(outcome, Park)
