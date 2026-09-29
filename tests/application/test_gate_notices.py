# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices (application/gate_notices.py): every notice ends in a record of whether
anyone was told, and a gate still waiting is reminded about on its project's schedule."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository
from vibey.application.dto import GateReminderReport, HumanGateRecord, ProjectRecord
from vibey.application.gate_notices import GateNoticeService, GateReminder
from vibey.application.interfaces import (
    GateNoticeServiceInterface,
    GateNoticeStore,
    GateReminderInterface,
)
from vibey.domain.gate_notice import GateNotice, NoticeReason
from vibey.domain.phase import Phase

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)
ENABLED = {"notifications": {"enabled": True}}


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

    def events(self) -> list[tuple[str, str]]:
        return [(level, event) for level, event, _ in self.lines]


class _Sink:
    def __init__(self, result: Mapping[str, object] | Exception | None = None) -> None:
        self._result = result if result is not None else {"desktop": True, "webhooks": []}
        self.calls: list[dict[str, object]] = []

    async def notify(self, **kwargs: object) -> Mapping[str, object]:
        self.calls.append(kwargs)
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


class _Store:
    def __init__(
        self,
        recorded: Mapping[UUID, frozenset[int]] | None = None,
        *,
        fail_record: bool = False,
        fail_read: bool = False,
    ) -> None:
        self._recorded = dict(recorded or {})
        self._fail_record = fail_record
        self._fail_read = fail_read
        self.records: list[GateNotice] = []

    async def record(self, notice: GateNotice) -> bool:
        if self._fail_record:
            raise ConnectionError("ledger down")
        self.records.append(notice)
        return True

    async def recorded(self, project_id: UUID) -> Mapping[UUID, frozenset[int]]:
        if self._fail_read:
            raise ConnectionError("ledger down")
        return self._recorded


class _Clock:
    def __init__(self, now: datetime = NOW) -> None:
        self.now_value = now

    def now(self) -> datetime:
        return self.now_value


class _Projects:
    def __init__(self, *projects: ProjectRecord, fail: bool = False) -> None:
        self._projects = {project.project_id: project for project in projects}
        self._fail = fail

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._projects.get(project_id)

    async def get_latest(self) -> ProjectRecord | None:
        return None

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        if self._fail:
            raise ConnectionError("database down")
        return tuple(self._projects.values())


def _project(name: str = "demo", config: Mapping[str, object] | None = None) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name=name,
        repo_path=Path("/tmp/demo"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=10,
        config=dict(config if config is not None else ENABLED),
        created_at=NOW,
        updated_at=NOW,
    )


def _gate(
    project_id: UUID, *, kind: str = "approval", waited: timedelta = timedelta(0)
) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=project_id,
        job_id=uuid4(),
        kind=kind,
        prompt="answer me",
        options=(),
        default_answer=None,
        answer=None,
        raised_at=NOW - waited,
        timeout_at=None,
        answered_at=None,
        answered_by=None,
    )


# -- GateNoticeService ------------------------------------------------------------------


def test_the_service_satisfies_its_declared_seam() -> None:
    service = GateNoticeService(sink=None, store=None, logger=_Logger())
    assert isinstance(service, GateNoticeServiceInterface)
    assert isinstance(_Store(), GateNoticeStore)


async def test_a_delivered_notice_is_recorded_and_said() -> None:
    sink, store, logger = _Sink(), _Store(), _Logger()
    gate = _gate(uuid4())
    notice = await GateNoticeService(sink=sink, store=store, logger=logger).deliver(
        gate, notice=0, config=ENABLED
    )
    assert notice.delivered
    assert notice.channels == {"desktop": True, "webhooks": []}
    assert store.records == [notice]
    assert logger.events() == [("info", "gate.notified")]
    assert sink.calls[0]["payload"] == {
        "gate_id": str(gate.gate_id),
        "gate_kind": "approval",
        "job_id": str(gate.job_id),
        "notice": 0,
    }
    assert sink.calls[0]["title"] == "Human Gate Raised"
    assert sink.calls[0]["config"] == ENABLED


@pytest.mark.parametrize(
    ("config", "reason"),
    [
        ({}, NoticeReason.DISABLED),
        ({"notifications": {"enabled": False}}, NoticeReason.DISABLED),
        ({"notifications": {"enabled": True, "desktop": False}}, NoticeReason.NO_CHANNEL),
        ({"notifications": {"enabled": "yes"}}, NoticeReason.CONFIG_INVALID),
    ],
)
async def test_nobody_can_be_told_is_recorded_and_said_loudly(
    config: Mapping[str, object], reason: NoticeReason
) -> None:
    sink, store, logger = _Sink(), _Store(), _Logger()
    notice = await GateNoticeService(sink=sink, store=store, logger=logger).deliver(
        _gate(uuid4()), notice=0, config=config
    )
    assert notice.reason is reason
    assert notice.detail
    assert sink.calls == []
    assert store.records == [notice]
    assert logger.events() == [("warning", "gate.notice_undeliverable")]
    assert logger.lines[0][2]["reason"] == str(reason)


async def test_a_config_of_none_is_notifications_off() -> None:
    notice = await GateNoticeService(sink=_Sink(), store=None, logger=_Logger()).deliver(
        _gate(uuid4()), notice=0, config=None
    )
    assert notice.reason is NoticeReason.DISABLED


async def test_a_process_with_no_sink_says_so() -> None:
    notice = await GateNoticeService(sink=None, store=None, logger=_Logger()).deliver(
        _gate(uuid4()), notice=0, config=ENABLED
    )
    assert notice.reason is NoticeReason.UNWIRED


async def test_a_sink_that_raises_is_a_failed_notice_not_a_lost_gate() -> None:
    logger = _Logger()
    notice = await GateNoticeService(
        sink=_Sink(RuntimeError("no desktop")), store=_Store(), logger=logger
    ).deliver(_gate(uuid4()), notice=0, config=ENABLED)
    assert notice.reason is NoticeReason.FAILED
    assert notice.detail == "RuntimeError('no desktop')"
    assert logger.lines[0][2]["error"] == "RuntimeError('no desktop')"


async def test_a_channel_that_did_not_deliver_is_a_failed_notice() -> None:
    notice = await GateNoticeService(
        sink=_Sink({"desktop": False, "webhooks": []}), store=_Store(), logger=_Logger()
    ).deliver(_gate(uuid4()), notice=0, config=ENABLED)
    assert notice.reason is NoticeReason.FAILED
    assert notice.detail == "desktop delivery returned false"
    assert notice.channels == {"desktop": False, "webhooks": []}


async def test_a_store_that_fails_is_said_and_the_notice_stands() -> None:
    logger = _Logger()
    notice = await GateNoticeService(
        sink=_Sink(), store=_Store(fail_record=True), logger=logger
    ).deliver(_gate(uuid4()), notice=0, config=ENABLED)
    assert notice.delivered
    assert logger.events() == [("warning", "gate.notice_unrecorded"), ("info", "gate.notified")]
    assert logger.lines[0][2]["error"] == "ConnectionError('ledger down')"


@pytest.mark.parametrize(
    ("kind", "notice", "waited", "title", "message"),
    [
        ("budget_exhausted", 0, 0, "Budget Exceeded", "A budget decision is needed to continue."),
        (
            "budget_exhausted",
            2,
            2 * 86_400,
            "Budget Decision Still Waiting",
            "A budget decision has been needed for 2 days; `vibey gates` lists it (reminder 2).",
        ),
        (
            "approval",
            1,
            86_400,
            "Human Gate Still Waiting",
            "Your response has been needed for 1 day; `vibey gates` lists it (reminder 1).",
        ),
        (
            "approval",
            1,
            3 * 3_600,
            "Human Gate Still Waiting",
            "Your response has been needed for 3 hours; `vibey gates` lists it (reminder 1).",
        ),
        (
            "approval",
            1,
            3_600,
            "Human Gate Still Waiting",
            "Your response has been needed for 1 hour; `vibey gates` lists it (reminder 1).",
        ),
        (
            "approval",
            1,
            60,
            "Human Gate Still Waiting",
            "Your response has been needed for under an hour; `vibey gates` lists it (reminder 1).",
        ),
    ],
)
async def test_a_notice_is_a_short_cue_never_the_prompt(
    kind: str, notice: int, waited: float, title: str, message: str
) -> None:
    sink = _Sink()
    await GateNoticeService(sink=sink, store=None, logger=_Logger()).deliver(
        _gate(uuid4(), kind=kind), notice=notice, config=ENABLED, waited_seconds=waited
    )
    assert sink.calls[0]["title"] == title
    assert sink.calls[0]["message"] == message
    assert sink.calls[0]["kind"] == (
        "budget_exceeded" if kind == "budget_exhausted" else ("human_gate_raised")
    )


# -- GateReminder -----------------------------------------------------------------------


class _Notices:
    def __init__(self) -> None:
        self.sent: list[tuple[UUID, int, float]] = []

    async def deliver(
        self,
        gate: HumanGateRecord,
        *,
        notice: int,
        config: Mapping[str, object] | None,
        waited_seconds: float = 0.0,
    ) -> GateNotice:
        self.sent.append((gate.gate_id, notice, waited_seconds))
        return GateNotice(
            project_id=gate.project_id,
            gate_id=gate.gate_id,
            gate_kind=gate.kind,
            job_id=gate.job_id,
            notice=notice,
        )


def _gates(*records: HumanGateRecord) -> FakeHumanGateRepository:
    gates = FakeHumanGateRepository()
    gates.raised = list(records)
    return gates


def _reminder(
    gates: FakeHumanGateRepository,
    projects: _Projects,
    store: _Store,
    notices: _Notices,
    *,
    logger: _Logger | None = None,
    clock: _Clock | None = None,
    interval: int = 300,
) -> GateReminder:
    return GateReminder(
        gates=gates,
        projects=projects,
        store=store,
        notices=notices,
        clock=clock or _Clock(),
        logger=logger or _Logger(),
        interval_seconds=interval,
    )


def test_the_reminder_satisfies_its_declared_seam() -> None:
    reminder = _reminder(_gates(), _Projects(), _Store(), _Notices())
    assert isinstance(reminder, GateReminderInterface)


async def test_each_gate_gets_the_one_notice_now_due() -> None:
    project = _project()
    fresh = _gate(project.project_id)  # no raise notice on record: gets one
    stale = _gate(project.project_id, waited=2 * DAY)  # reminded: 0 and 1 on record
    waiting = _gate(project.project_id, waited=timedelta(hours=3))  # not stale yet
    store = _Store({stale.gate_id: frozenset({0, 1}), waiting.gate_id: frozenset({0})})
    notices = _Notices()

    report = await _reminder(
        _gates(fresh, stale, waiting), _Projects(project), store, notices
    ).run()

    assert report.waiting == 3
    # Oldest first, as the gates are read.
    assert [(gate_id, number) for gate_id, number, _ in notices.sent] == [
        (stale.gate_id, 2),
        (fresh.gate_id, 0),
    ]
    assert [notice.notice for notice in report.sent] == [2, 0]
    assert report.ok


async def test_a_project_nobody_can_hear_is_said_once_and_not_reminded_about() -> None:
    project = _project(config={})
    said = _gate(project.project_id, waited=5 * DAY)
    unsaid = _gate(project.project_id, waited=5 * DAY)
    notices = _Notices()
    await _reminder(
        _gates(said, unsaid), _Projects(project), _Store({said.gate_id: frozenset({0})}), notices
    ).run()
    assert [(gate_id, number) for gate_id, number, _ in notices.sent] == [(unsaid.gate_id, 0)]


async def test_a_configuration_that_does_not_parse_is_treated_as_silent() -> None:
    project = _project(config={"notifications": {"max_reminders": -1}})
    gate = _gate(project.project_id, waited=5 * DAY)
    notices = _Notices()
    await _reminder(
        _gates(gate), _Projects(project), _Store({gate.gate_id: frozenset({0})}), notices
    ).run()
    assert notices.sent == []


async def test_a_dry_run_plans_and_sends_nothing() -> None:
    project = _project()
    gate = _gate(project.project_id, waited=DAY)
    notices, logger = _Notices(), _Logger()
    report = await _reminder(
        _gates(gate),
        _Projects(project),
        _Store({gate.gate_id: frozenset({0})}),
        notices,
        logger=logger,
    ).run(project.project_id, dry_run=True)
    assert notices.sent == []
    assert report.dry_run
    assert [(planned.gate_id, planned.notice) for planned in report.planned] == [(gate.gate_id, 1)]
    assert report.planned[0].waited_seconds == DAY.total_seconds()
    assert logger.events() == [("info", "gate.reminders_planned")]


async def test_one_project_is_swept_alone() -> None:
    mine, other = _project("mine"), _project("other")
    gate, elsewhere = _gate(mine.project_id), _gate(other.project_id)
    notices = _Notices()
    report = await _reminder(
        _gates(gate, elsewhere), _Projects(mine, other), _Store(), notices
    ).run(mine.project_id)
    assert [gate_id for gate_id, _, _ in notices.sent] == [gate.gate_id]
    assert report.project_id == mine.project_id


async def test_an_unknown_project_sweeps_nothing() -> None:
    notices = _Notices()
    report = await _reminder(_gates(), _Projects(), _Store(), notices).run(uuid4())
    assert report.waiting == 0
    assert notices.sent == []


async def test_a_gate_whose_project_is_gone_is_not_reminded_about() -> None:
    notices = _Notices()
    report = await _reminder(_gates(_gate(uuid4())), _Projects(), _Store(), notices).run()
    assert report.waiting == 0
    assert notices.sent == []


async def test_unreadable_gates_are_reported_and_nothing_is_sent() -> None:
    logger = _Logger()
    report = await _reminder(
        _gates(), _Projects(fail=True), _Store(), _Notices(), logger=logger
    ).run()
    assert not report.ok
    assert report.unreadable == ("open gates: database down",)
    assert logger.events() == [("warning", "gate.remind_unreadable")]
    assert logger.lines[0][2]["project_id"] == "all"


async def test_unreadable_notices_skip_that_project_and_are_reported() -> None:
    project = _project("ledgerless")
    notices, logger = _Notices(), _Logger()
    report = await _reminder(
        _gates(_gate(project.project_id)),
        _Projects(project),
        _Store(fail_read=True),
        notices,
        logger=logger,
    ).run(project.project_id)
    assert notices.sent == []
    assert report.unreadable == ("project ledgerless: notices on record: ledger down",)
    assert logger.lines[0][2]["project_id"] == str(project.project_id)


async def test_run_if_due_sweeps_at_most_once_per_interval_per_project() -> None:
    project = _project()
    gate = _gate(project.project_id)
    clock, notices = _Clock(), _Notices()
    reminder = _reminder(
        _gates(gate), _Projects(project), _Store(), notices, clock=clock, interval=300
    )

    first = await reminder.run_if_due(project.project_id)
    assert isinstance(first, GateReminderReport)
    assert await reminder.run_if_due(project.project_id) is None
    clock.now_value = NOW + timedelta(seconds=300)
    assert await reminder.run_if_due(project.project_id) is not None
    assert len(notices.sent) == 2


async def test_a_waiting_time_is_never_negative() -> None:
    project = _project()
    future = replace(_gate(project.project_id), raised_at=NOW + DAY)
    notices = _Notices()
    await _reminder(_gates(future), _Projects(project), _Store(), notices).run()
    assert notices.sent == [(future.gate_id, 0, 0.0)]
