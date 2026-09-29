# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Defect triage (application/defect_triage.py): an exhausted job whose last failures were
all one failure parks on a `defect` gate that offers no more attempts; varied failures keep
their grant; and every step fails open to the grant."""

from dataclasses import replace
from uuid import uuid4

import pytest

from tests.application.fakes import make_job
from vibey.application.defect_triage import DEFECT_GATE, DefectGate, DefectTriage
from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces import (
    DefectGateInterface,
    DefectTriageInterface,
    JobFailureHistory,
)
from vibey.domain.defect import FAILURE_NORMALIZER, DefectVerdict, FailureSignature
from vibey.domain.job import (
    ATTEMPTS_EXHAUSTED_GATE_KIND,
    DEFECT_GATE_KIND,
    ESCALATION_EXHAUSTED_GATE_KIND,
    FailureClass,
)

GRANT = HumanGateRequest(kind=ATTEMPTS_EXHAUSTED_GATE_KIND, prompt="grant more?")


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, object]]] = []

    def bind(self, **kwargs: object) -> "_Logger":
        return self

    def debug(self, event: str, **kwargs: object) -> None:
        self.lines.append(("debug", event, dict(kwargs)))

    def info(self, event: str, **kwargs: object) -> None:
        self.lines.append(("info", event, dict(kwargs)))

    def warning(self, event: str, **kwargs: object) -> None:
        self.lines.append(("warning", event, dict(kwargs)))

    def error(self, event: str, **kwargs: object) -> None:
        self.lines.append(("error", event, dict(kwargs)))


class _History:
    """Newest last in `records`; `recent` returns newest first, as the ledger reads."""

    def __init__(self, *, fail_record: bool = False, fail_read: bool = False) -> None:
        self.records: list[tuple[JobRecord, FailureSignature, str]] = []
        self._fail_record = fail_record
        self._fail_read = fail_read

    async def record(self, job: JobRecord, signature: FailureSignature, *, detail: str) -> None:
        if self._fail_record:
            raise ConnectionError("ledger down")
        self.records.append((job, signature, detail))

    async def recent(self, job: JobRecord, *, limit: int) -> tuple[FailureSignature, ...]:
        if self._fail_read:
            raise ConnectionError("ledger down")
        mine = [signature for record_job, signature, _ in self.records if record_job.id == job.id]
        return tuple(reversed(mine))[:limit]


def _job() -> JobRecord:
    return replace(make_job(uuid4(), attempts=7), work_item_id="W-1")


def test_the_triage_and_gate_satisfy_their_declared_seams() -> None:
    assert isinstance(DefectTriage(history=_History(), logger=_Logger()), DefectTriageInterface)
    assert isinstance(DEFECT_GATE, DefectGateInterface)
    assert isinstance(_History(), JobFailureHistory)


async def test_each_failure_is_recorded_with_its_signature() -> None:
    history = _History()
    job = _job()
    await DefectTriage(history=history, logger=_Logger()).record(
        job, FailureClass.WORK, "ImportError at 2026-09-28T12:00:00Z"
    )
    ((recorded_job, signature, detail),) = history.records
    assert recorded_job == job
    assert detail == "ImportError at 2026-09-28T12:00:00Z"
    assert signature == FAILURE_NORMALIZER.signature("work", detail)


async def test_a_failure_that_cannot_be_recorded_is_said_not_raised() -> None:
    logger = _Logger()
    await DefectTriage(history=_History(fail_record=True), logger=logger).record(
        _job(), FailureClass.ENGINE, "boom"
    )
    assert [(level, event) for level, event, _ in logger.lines] == [
        ("warning", "job.failure_unrecorded")
    ]
    assert logger.lines[0][2]["error"] == "ConnectionError('ledger down')"


async def _failed(triage: DefectTriage, job: JobRecord, *details: str) -> None:
    for detail in details:
        await triage.record(job, FailureClass.WORK, detail)


@pytest.mark.parametrize("kind", [ATTEMPTS_EXHAUSTED_GATE_KIND, ESCALATION_EXHAUSTED_GATE_KIND])
async def test_identical_failures_raise_a_defect_gate_instead_of_a_grant(kind: str) -> None:
    logger = _Logger()
    triage = DefectTriage(history=_History(), logger=logger, threshold=3)
    job = _job()
    await _failed(
        triage,
        job,
        "on attempt 5 after 12s: ImportError: no module named greeter",
        "on attempt 6 after 9s: ImportError: no module named greeter",
        "on attempt 7 after 31s: ImportError: no module named greeter",
    )

    gate = await triage.triage(job, HumanGateRequest(kind=kind, prompt="grant more?"))

    assert gate.kind == DEFECT_GATE_KIND
    assert gate.options == ("requeue", "abandon")
    assert "last 3 attempts" in gate.prompt
    assert "ImportError: no module named greeter" in gate.prompt
    assert "max_attempts" not in gate.prompt
    assert [(level, event) for level, event, _ in logger.lines] == [("warning", "job.defect")]
    assert logger.lines[0][2]["instead_of"] == kind


async def test_varied_failures_keep_their_grant() -> None:
    triage = DefectTriage(history=_History(), logger=_Logger(), threshold=3)
    job = _job()
    await _failed(triage, job, "ImportError", "ImportError", "AssertionError: 3 != 4")
    assert await triage.triage(job, GRANT) is GRANT


async def test_too_few_failures_keep_their_grant() -> None:
    triage = DefectTriage(history=_History(), logger=_Logger(), threshold=3)
    job = _job()
    await _failed(triage, job, "ImportError", "ImportError")
    assert await triage.triage(job, GRANT) is GRANT


async def test_a_gate_that_offers_no_grant_is_left_alone() -> None:
    triage = DefectTriage(history=_History(), logger=_Logger(), threshold=2)
    job = _job()
    await _failed(triage, job, "boom", "boom")
    request = HumanGateRequest(kind="approval", prompt="accept?")
    assert await triage.triage(job, request) is request


async def test_the_check_switched_off_keeps_every_grant() -> None:
    triage = DefectTriage(history=_History(), logger=_Logger(), threshold=0)
    job = _job()
    await _failed(triage, job, "boom", "boom", "boom")
    assert await triage.triage(job, GRANT) is GRANT


async def test_history_that_cannot_be_read_keeps_the_grant_and_says_so() -> None:
    logger = _Logger()
    triage = DefectTriage(history=_History(fail_read=True), logger=logger)
    assert await triage.triage(_job(), GRANT) is GRANT
    assert [(level, event) for level, event, _ in logger.lines] == [
        ("warning", "job.failure_history_unreadable")
    ]


def test_the_defect_prompt_names_the_item_when_there_is_one() -> None:
    signature = FailureSignature(failure_class="work", digest="0123456789abcdef", excerpt="boom")
    verdict = DefectVerdict(signature=signature, identical=4)
    with_item = DefectGate().request(_job(), verdict)
    without_item = DefectGate().request(make_job(uuid4()), verdict)
    assert "(work item 'W-1')" in with_item.prompt
    assert "work item" not in without_item.prompt
    assert "signature 0123456789abcdef" in without_item.prompt
    assert "--choice requeue" in without_item.prompt
    assert "--choice abandon" in without_item.prompt
