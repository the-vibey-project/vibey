# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate timeouts (application/gate_timeouts.py): a gate resolves to its own default only
where its project declared that kind may, and only through the one answer path."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from tests.application.test_gate_notices import (
    NOW,
    _Clock,
    _gate,
    _gates,
    _Logger,
    _project,
    _Projects,
)
from vibey.application.dto import GateAnswerOutcome
from vibey.application.gate_timeouts import GATE_TIMEOUT_ACTOR, GateTimeoutSweep
from vibey.application.interfaces import GateTimeoutSweepInterface

DECLARED = {"human_gates": {"timeout_defaults": {"choice": 60}}}


class _Answers:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[UUID, dict[str, object], str | None, str | None]] = []
        self._fail = fail

    async def answer(
        self,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        by: str | None = None,
        request_id: str | None = None,
    ) -> GateAnswerOutcome:
        if self._fail:
            raise ConnectionError("database down")
        self.calls.append((gate_id, dict(answer), by, request_id))
        return GateAnswerOutcome(record=None)  # type: ignore[arg-type]

    def derived_request_id(self, source: str, gate_id: UUID, answer: Mapping[str, object]) -> str:
        return f"{source}:{gate_id}:{sorted(answer.items())}"


def _choice_gate(project_id: UUID, *, waited: timedelta, default: str | None = "local_only"):  # type: ignore[no-untyped-def]
    return replace(_gate(project_id, kind="choice", waited=waited), default_answer=default)


def _sweep(gates, projects, answers, *, logger=None, interval=300):  # type: ignore[no-untyped-def]
    return GateTimeoutSweep(
        gates=gates,
        projects=projects,
        answers=answers,
        clock=_Clock(),
        logger=logger or _Logger(),
        interval_seconds=interval,
    )


def test_the_sweep_satisfies_its_declared_seam() -> None:
    sweep = _sweep(_gates(), _Projects(), _Answers())
    assert isinstance(sweep, GateTimeoutSweepInterface)


async def test_a_declared_gate_that_has_waited_resolves_to_its_default() -> None:
    project = _project(config=DECLARED)
    gate = _choice_gate(project.project_id, waited=timedelta(minutes=61))
    answers = _Answers()
    logger = _Logger()

    report = await _sweep(_gates(gate), _Projects(project), answers, logger=logger).run()

    assert [(gid, answer, by) for gid, answer, by, _ in answers.calls] == [
        (gate.gate_id, {"choice": "local_only"}, GATE_TIMEOUT_ACTOR)
    ]
    assert answers.calls[0][3] is not None  # a derived id: a replayed sweep is a no-op
    assert [r.gate_id for r in report.resolved] == [gate.gate_id]
    assert ("info", "gate.resolved_by_timeout") in logger.events()


async def test_silence_is_not_consent_for_an_undeclared_project() -> None:
    project = _project(config={})
    gate = _choice_gate(project.project_id, waited=timedelta(days=30))
    answers = _Answers()

    report = await _sweep(_gates(gate), _Projects(project), answers).run()

    assert answers.calls == []
    assert report.resolved == ()


async def test_a_gate_still_inside_its_wait_is_left_for_a_person() -> None:
    project = _project(config=DECLARED)
    gate = _choice_gate(project.project_id, waited=timedelta(minutes=59))
    answers = _Answers()

    await _sweep(_gates(gate), _Projects(project), answers).run()

    assert answers.calls == []


async def test_an_undeclared_kind_in_a_declaring_project_still_waits() -> None:
    project = _project(config=DECLARED)
    gate = replace(
        _gate(project.project_id, kind="deploy_demo_review", waited=timedelta(days=30)),
        default_answer="approve",
    )
    answers = _Answers()

    await _sweep(_gates(gate), _Projects(project), answers).run()

    assert answers.calls == []


async def test_a_project_whose_declaration_cannot_be_honoured_answers_nothing() -> None:
    project = _project(config={"human_gates": {"timeout_defaults": {"approval": 1}}})
    gate = _choice_gate(project.project_id, waited=timedelta(days=30))
    answers = _Answers()
    logger = _Logger()

    report = await _sweep(_gates(gate), _Projects(project), answers, logger=logger).run()

    assert answers.calls == []
    assert len(report.refused) == 1
    assert "approval" in report.refused[0]
    assert ("warning", "gate.timeout_config_invalid") in logger.events()


async def test_an_answer_that_fails_is_reported_and_the_sweep_goes_on() -> None:
    project = _project(config=DECLARED)
    gate = _choice_gate(project.project_id, waited=timedelta(minutes=61))
    logger = _Logger()

    report = await _sweep(
        _gates(gate), _Projects(project), _Answers(fail=True), logger=logger
    ).run()

    assert report.resolved == ()
    assert len(report.failed) == 1
    assert "database down" in report.failed[0]
    assert ("warning", "gate.timeout_answer_failed") in logger.events()


async def test_unreadable_gates_are_reported_never_guessed() -> None:
    report = await _sweep(_gates(), _Projects(fail=True), _Answers()).run()

    assert report.resolved == ()
    assert len(report.refused) == 1


async def test_one_project_scope_reads_only_that_project() -> None:
    mine = _project(config=DECLARED)
    other = _project(name="other", config=DECLARED)
    my_gate = _choice_gate(mine.project_id, waited=timedelta(minutes=61))
    other_gate = _choice_gate(other.project_id, waited=timedelta(minutes=61))
    answers = _Answers()

    await _sweep(_gates(my_gate, other_gate), _Projects(mine, other), answers).run(mine.project_id)

    assert [gid for gid, *_ in answers.calls] == [my_gate.gate_id]


async def test_a_gate_whose_project_is_gone_is_skipped() -> None:
    orphan = _choice_gate(_project().project_id, waited=timedelta(days=1))
    answers = _Answers()

    await _sweep(_gates(orphan), _Projects(), answers).run()

    assert answers.calls == []


async def test_a_project_scope_with_no_project_answers_nothing() -> None:
    project = _project(config=DECLARED)
    answers = _Answers()

    await _sweep(_gates(), _Projects(), answers).run(project.project_id)

    assert answers.calls == []


async def test_the_sweep_runs_at_most_once_per_interval_per_scope() -> None:
    project = _project(config=DECLARED)
    sweep = _sweep(_gates(), _Projects(project), _Answers(), interval=300)

    assert await sweep.run_if_due(None) is not None
    assert await sweep.run_if_due(None) is None
    assert await sweep.run_if_due(project.project_id) is not None


def test_now_is_the_reminder_suites_clock() -> None:
    assert _Clock().now() == NOW
