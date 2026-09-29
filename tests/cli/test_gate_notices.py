# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey gates --remind` and `vibey doctor`'s gate-notices line, over a fake app: every
branch of the command, the presenter and the doctor line."""

import asyncio
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import typer

from vibey.application.dto import GateReminderReport, HumanGateRecord, PlannedNotice, ProjectRecord
from vibey.cli.gate_notices import (
    GATE_NOTICE_DOCTOR,
    GATE_READERS,
    GATE_REMINDERS,
    GATE_REMINDERS_PRESENTER,
    GateNoticeDoctor,
    GateReaders,
    GateRemindersCommand,
)
from vibey.cli.interfaces import (
    GateNoticeDoctorInterface,
    GateReadersOpenerInterface,
    GateRemindersCommandInterface,
    GateRemindersPresenterInterface,
)
from vibey.domain.gate_notice import GateNotice, NoticeReason
from vibey.domain.phase import Phase

AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
PROJECT = uuid4()


def test_the_shared_instances_satisfy_their_declared_seams() -> None:
    assert isinstance(GATE_REMINDERS, GateRemindersCommandInterface)
    assert isinstance(GATE_REMINDERS_PRESENTER, GateRemindersPresenterInterface)
    assert isinstance(GATE_NOTICE_DOCTOR, GateNoticeDoctorInterface)
    assert isinstance(GATE_READERS, GateReadersOpenerInterface)


def _notice(number: int, **values: object) -> GateNotice:
    return GateNotice(
        project_id=PROJECT,
        gate_id=UUID(int=number + 1),
        gate_kind="approval",
        job_id=None,
        notice=number,
        **values,  # type: ignore[arg-type]
    )


def test_the_presenter_says_what_was_sent_and_what_was_not() -> None:
    report = GateReminderReport(
        project_id=None,
        dry_run=False,
        waiting=3,
        sent=(
            _notice(0, channels={"desktop": True}),
            _notice(2, reason=NoticeReason.DISABLED, detail="nobody will be told"),
            _notice(1, reason=NoticeReason.FAILED),
        ),
        unreadable=("project x: notices on record: down",),
    )
    assert GATE_REMINDERS_PRESENTER.lines(report) == [
        "3 open gates; 3 notices sent",
        f"  told    raise notice gate {UUID(int=1)} (approval)",
        f"  UNDELIVERABLE (disabled) reminder 2 gate {UUID(int=3)} (approval)",
        "          nobody will be told",
        f"  UNDELIVERABLE (failed) reminder 1 gate {UUID(int=2)} (approval)",
        "  UNREADABLE project x: notices on record: down: nothing was sent for it",
    ]
    document = json.loads(GATE_REMINDERS_PRESENTER.json(report))
    assert document["project_id"] is None
    assert document["ok"] is False
    assert [entry["delivered"] for entry in document["sent"]] == [True, False, False]
    assert document["sent"][1]["reason"] == "disabled"


def test_the_presenter_lists_a_dry_run_as_due() -> None:
    planned = PlannedNotice(
        project_id=PROJECT, gate_id=UUID(int=9), gate_kind="defect", notice=1, waited_seconds=90_000
    )
    report = GateReminderReport(project_id=PROJECT, dry_run=True, waiting=1, planned=(planned,))
    assert GATE_REMINDERS_PRESENTER.lines(report) == [
        "1 open gate; 1 notice due",
        f"  due     reminder 1 gate {UUID(int=9)} (defect), waiting 25h",
    ]
    document = json.loads(GATE_REMINDERS_PRESENTER.json(report))
    assert document["project_id"] == str(PROJECT)
    assert document["planned"] == [
        {
            "project_id": str(PROJECT),
            "gate_id": str(UUID(int=9)),
            "gate_kind": "defect",
            "notice": 1,
            "waited_seconds": 90_000,
        }
    ]


@dataclass
class _Reminder:
    report: GateReminderReport
    calls: list[tuple[UUID | None, bool]] = field(default_factory=list)

    async def run(self, project_id: UUID | None = None, *, dry_run: bool = False) -> Any:
        self.calls.append((project_id, dry_run))
        return self.report

    async def run_if_due(self, project_id: UUID) -> Any:
        return None


@dataclass
class _Projects:
    known: Mapping[UUID, ProjectRecord] = field(default_factory=dict)
    fail: bool = False

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self.known.get(project_id)

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        if self.fail:
            raise ConnectionError("database down")
        return tuple(self.known.values())


@dataclass
class _Gates:
    open: tuple[HumanGateRecord, ...] = ()

    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        return self.open


def _app(**resources: object) -> Any:
    @asynccontextmanager
    async def open_app() -> AsyncIterator[Any]:
        yield type("R", (), resources)()

    return open_app


def _project(name: str, config: Mapping[str, object]) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name=name,
        repo_path=Path("/tmp/x"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config=dict(config),
        created_at=AT,
        updated_at=AT,
    )


def test_the_command_runs_one_sweep_and_prints_it(capsys: pytest.CaptureFixture[str]) -> None:
    project = _project("demo", {})
    reminder = _Reminder(GateReminderReport(project_id=project.project_id, dry_run=True))
    command = GateRemindersCommand(
        open_app=_app(gate_reminder=reminder, projects=_Projects({project.project_id: project}))
    )
    asyncio.run(command.run(project.project_id, as_json=False, dry_run=True))
    assert reminder.calls == [(project.project_id, True)]
    assert "0 open gates; 0 notices due" in capsys.readouterr().out

    asyncio.run(command.run(None, as_json=True, dry_run=False))
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_the_command_refuses_an_unknown_project(capsys: pytest.CaptureFixture[str]) -> None:
    reminder = _Reminder(GateReminderReport(project_id=None, dry_run=False))
    command = GateRemindersCommand(open_app=_app(gate_reminder=reminder, projects=_Projects()))
    with pytest.raises(typer.Exit) as caught:
        asyncio.run(command.run(uuid4(), as_json=True, dry_run=False))
    assert caught.value.exit_code == 1
    assert reminder.calls == []
    assert "unknown project" in capsys.readouterr().err


def test_a_sweep_that_could_not_read_a_project_exits_1() -> None:
    report = GateReminderReport(project_id=None, dry_run=False, unreadable=("x",))
    command = GateRemindersCommand(
        open_app=_app(gate_reminder=_Reminder(report), projects=_Projects())
    )
    with pytest.raises(typer.Exit) as caught:
        asyncio.run(command.run(None, as_json=False, dry_run=False))
    assert caught.value.exit_code == 1


def _gate(project_id: UUID) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=project_id,
        job_id=None,
        kind="approval",
        prompt="?",
        options=(),
        default_answer=None,
        answer=None,
        raised_at=AT,
        timeout_at=None,
        answered_at=None,
        answered_by=None,
    )


def _doctor(
    gates: _Gates, projects: _Projects, *, url: str = "postgresql://x/y"
) -> GateNoticeDoctor:
    class _Readers:
        @asynccontextmanager
        async def open(self, dsn: str) -> AsyncIterator[Any]:
            assert dsn == url.strip()
            yield GateReaders(gates=gates, projects=projects)  # type: ignore[arg-type]

    return GateNoticeDoctor(readers=_Readers(), environ=lambda: {"VIBEY_PG_URL": url})


def test_the_doctor_line_without_a_database_is_unknown() -> None:
    line = asyncio.run(_doctor(_Gates(), _Projects(), url=" ").line())
    assert line.startswith("UNKNOWN gate-notices")
    assert "VIBEY_PG_URL is not set" in line


def test_the_doctor_line_when_the_gates_cannot_be_read_is_unknown() -> None:
    line = asyncio.run(_doctor(_Gates(), _Projects(fail=True)).line())
    assert line.startswith("UNKNOWN gate-notices")
    assert "database down" in line


def test_the_doctor_line_with_no_gates_passes() -> None:
    orphan = _gate(uuid4())  # its project is gone: not waiting on anyone
    assert asyncio.run(_doctor(_Gates((orphan,)), _Projects()).line()) == (
        "PASS gate-notices         no open gates"
    )


def test_the_doctor_line_passes_when_every_project_has_a_channel() -> None:
    heard = _project("heard", {"notifications": {"enabled": True}})
    line = asyncio.run(
        _doctor(_Gates((_gate(heard.project_id),)), _Projects({heard.project_id: heard})).line()
    )
    assert line == (
        "PASS gate-notices         1 gate waiting; every one's project has a notification channel"
    )


def test_the_doctor_line_counts_the_gates_nobody_will_be_told_about() -> None:
    off = _project("alpha", {})
    mute = _project("beta", {"notifications": {"enabled": True, "desktop": False}})
    broken = _project("gamma", {"notifications": {"enabled": "yes"}})
    heard = _project("delta", {"notifications": {"enabled": True}})
    projects = _Projects({p.project_id: p for p in (off, mute, broken, heard)})
    gates = _Gates(
        (
            _gate(off.project_id),
            _gate(off.project_id),
            _gate(mute.project_id),
            _gate(broken.project_id),
            _gate(heard.project_id),
        )
    )

    line = asyncio.run(_doctor(gates, projects).line())

    assert line.startswith(
        "WARN gate-notices         4 gates waiting, nobody will be told; 1 more will be: "
        "alpha 2 (notifications disabled), beta 1 (notifications on, but no channel), "
        "gamma 1 ([notifications] does not parse)."
    )
    assert "Set [notifications] enabled = true" in line

    only = _Projects({off.project_id: off})
    assert asyncio.run(_doctor(_Gates((_gate(off.project_id),)), only).line()).startswith(
        "WARN gate-notices         1 gate waiting, nobody will be told: alpha 1"
    )


def test_the_shared_doctor_reads_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    assert asyncio.run(GATE_NOTICE_DOCTOR.line()).startswith("UNKNOWN gate-notices")
