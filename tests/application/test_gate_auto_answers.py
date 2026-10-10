# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`--auto-answer` (application/gate_auto_answers.py): the operator's flag lets a worker answer
the interview and the retry gates of one project, through the one answer path, up to its limit."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from tests.application.fakes import FakeHumanGateRepository
from tests.application.test_gate_notices import NOW, _Clock, _gate, _gates, _Logger
from tests.application.test_gate_timeouts import _Answers
from vibey.application.gate_auto_answers import GATE_AUTO_ANSWER_ACTOR, GateAutoAnswerSweep
from vibey.application.interfaces import GateAutoAnswerSweepInterface
from vibey.domain.gate_auto_answer import GateAutoAnswerPolicy

PROJECT = uuid4()


def _sweep(gates, answers, *, limit=30, logger=None):  # type: ignore[no-untyped-def]
    return GateAutoAnswerSweep(
        gates=gates,
        answers=answers,
        policy=GateAutoAnswerPolicy(limit=limit),
        clock=_Clock(),
        logger=logger or _Logger(),
    )


def _kind(kind: str, *, waited: timedelta = timedelta(minutes=5), project: UUID = PROJECT):  # type: ignore[no-untyped-def]
    return _gate(project, kind=kind, waited=waited)


def test_the_sweep_satisfies_its_declared_seam() -> None:
    assert isinstance(_sweep(_gates(), _Answers()), GateAutoAnswerSweepInterface)


async def test_an_answerable_gate_is_answered_through_the_one_path_and_recorded() -> None:
    gate = _kind("escalation_exhausted")
    answers = _Answers()
    logger = _Logger()

    report = await _sweep(_gates(gate), answers, logger=logger).run(PROJECT)

    ((gid, answer, by, request_id),) = answers.calls
    assert (gid, answer, by) == (gate.gate_id, {"max_attempts": 10}, GATE_AUTO_ANSWER_ACTOR)
    assert request_id is not None  # derived: a replayed sweep is a no-op
    (done,) = report.answered
    assert (done.gate_id, done.gate_kind, done.answer) == (
        gate.gate_id,
        "escalation_exhausted",
        {"max_attempts": 10},
    )
    assert done.waited_seconds == 300.0
    assert ("info", "gate.auto_answered") in logger.events()
    assert report.waiting == 1 and report.left == () and not report.limit_reached


async def test_a_spending_gate_and_every_other_kind_are_left_and_named() -> None:
    spend, approval, question = _kind("budget_exhausted"), _kind("approval"), _kind("question")
    answers = _Answers()

    report = await _sweep(_gates(spend, approval, question), answers).run(PROJECT)

    assert [gid for gid, *_ in answers.calls] == [question.gate_id]
    assert report.left == (
        f"budget_exhausted gate {spend.gate_id}",
        f"approval gate {approval.gate_id}",
    )
    assert report.waiting == 3


async def test_one_project_is_swept_and_only_that_one() -> None:
    other = uuid4()
    mine, theirs = _kind("question"), _kind("question", project=other)
    answers = _Answers()

    await _sweep(_gates(mine, theirs), answers).run(PROJECT)
    assert [gid for gid, *_ in answers.calls] == [mine.gate_id]

    everyone = _Answers()
    await _sweep(_gates(mine, theirs), everyone).run(None)
    assert {gid for gid, *_ in everyone.calls} == {mine.gate_id, theirs.gate_id}


async def test_gates_are_answered_oldest_first() -> None:
    older = _kind("question", waited=timedelta(hours=2))
    newer = _kind("question", waited=timedelta(minutes=1))
    answers = _Answers()
    await _sweep(_gates(newer, older), answers).run(PROJECT)
    assert [gid for gid, *_ in answers.calls] == [older.gate_id, newer.gate_id]


async def test_the_limit_stops_the_answers_and_is_said_once() -> None:
    gates = [_kind("question", waited=timedelta(minutes=n)) for n in (3, 2, 1)]
    answers = _Answers()
    sweep = _sweep(_gates(*gates), answers, limit=2)

    first = await sweep.run(PROJECT)
    assert len(first.answered) == 2 and first.limit_reached
    assert len(answers.calls) == 2

    second = await sweep.run(PROJECT)
    assert second.answered == () and not second.limit_reached
    assert second.waiting == 0
    assert len(answers.calls) == 2


async def test_a_limit_used_exactly_is_still_announced_when_nothing_is_left() -> None:
    answers = _Answers()
    report = await _sweep(_gates(_kind("question")), answers, limit=1).run(PROJECT)
    assert len(report.answered) == 1 and report.limit_reached


async def test_an_answer_that_fails_is_reported_does_not_count_and_the_sweep_goes_on() -> None:
    gate = _kind("delivery_exhausted")
    logger = _Logger()

    report = await _sweep(_gates(gate), _Answers(fail=True), limit=1, logger=logger).run(PROJECT)

    assert report.answered == ()
    assert len(report.failed) == 1 and "database down" in report.failed[0]
    assert not report.limit_reached
    assert ("warning", "gate.auto_answer_failed") in logger.events()


class _Unreadable(FakeHumanGateRepository):
    async def open_for_project(self, project_id: UUID):  # type: ignore[no-untyped-def]
        raise ConnectionError("gates unreadable")

    async def open_all(self):  # type: ignore[no-untyped-def]
        raise ConnectionError("gates unreadable")


async def test_a_read_that_fails_answers_nothing_and_says_why() -> None:
    answers = _Answers()
    logger = _Logger()
    for scope in (PROJECT, None):
        report = await _sweep(_Unreadable(), answers, logger=logger).run(scope)
        assert report.refused == ("open gates: gates unreadable",)
        assert report.answered == ()
    assert answers.calls == []
    assert ("warning", "gate.auto_answer_unreadable") in logger.events()


async def test_parallel_drive_loops_cannot_spend_the_limit_twice_on_one_gate() -> None:
    gate = _kind("question")
    repo = _gates(gate)

    class _AnsweringAnswers(_Answers):
        async def answer(self, gate_id, answer, *, by=None, request_id=None):  # type: ignore[no-untyped-def]
            outcome = await super().answer(gate_id, answer, by=by, request_id=request_id)
            repo.raised = [replace(g, answered_at=NOW) for g in repo.raised]
            return outcome

    answers = _AnsweringAnswers()
    sweep = _sweep(repo, answers, limit=5)
    await asyncio.gather(*(sweep.run(PROJECT) for _ in range(4)))
    assert len(answers.calls) == 1
