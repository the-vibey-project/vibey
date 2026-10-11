# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey retry`: stop old workers, grant attempts on exhausted gates, start a worker."""

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
import typer
from typer.testing import CliRunner

from vibey.application.dto import HumanGateRecord
from vibey.cli import main as cli_main
from vibey.cli.retry import RetryCommand
from vibey.domain.job import ATTEMPTS_EXHAUSTED_GATE_KIND
from vibey.infrastructure.worker_processes import ProcessInfo, StopPlan, StopReport

PROJECT = UUID("6b45e169-4653-4a8d-941c-7440249dc8ef")


def _gate(kind: str = ATTEMPTS_EXHAUSTED_GATE_KIND) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=PROJECT,
        job_id=uuid4(),
        kind=kind,
        prompt="p",
        options=(),
        default_answer=None,
        answer=None,
        raised_at=datetime.now(UTC),
        timeout_at=None,
        answered_at=None,
        answered_by=None,
    )


class FakeStopper:
    def __init__(self, *, survivors: tuple[int, ...] = (), workers: bool = True) -> None:
        row = ProcessInfo(pid=200, ppid=1, uid=501, state="S", argv=("vibey", "worker"))
        self._plan = StopPlan((row,) if workers else (), ())
        self._report = StopReport((200,), (), survivors)
        self.planned = self.stopped = False

    def plan(self) -> StopPlan:
        self.planned = True
        return self._plan

    def stop(self, plan: StopPlan, *, grace_seconds: float) -> StopReport:
        self.stopped = True
        return self._report


class FakeLauncher:
    def __init__(self) -> None:
        self.started: list[tuple[list[str], Path]] = []

    def start(self, args: Any, *, log: Path) -> int:
        self.started.append((list(args), log))
        return 777


class FakeResources:
    def __init__(self, gates: list[HumanGateRecord], *, known: bool = True) -> None:
        self.answered: list[tuple[UUID, Mapping[str, object], str | None, str | None]] = []
        outer = self

        class Projects:
            async def get(self, project_id: UUID) -> Any:
                return SimpleNamespace(name="ministry-section-4") if known else None

        class Gates:
            async def open_for_project(self, project_id: UUID) -> list[HumanGateRecord]:
                return gates

        class GateAnswers:
            async def answer(
                self,
                gate_id: UUID,
                payload: Mapping[str, object],
                *,
                by: str | None,
                request_id: str | None,
            ) -> None:
                outer.answered.append((gate_id, payload, by, request_id))

        self.projects, self.gates, self.gate_answers = Projects(), Gates(), GateAnswers()

    def opener(self) -> Any:
        @asynccontextmanager
        async def open_app() -> AsyncIterator[Any]:
            yield self

        return open_app


def _command(
    resources: FakeResources, stopper: FakeStopper | None = None
) -> tuple[RetryCommand, FakeStopper, FakeLauncher, list[str]]:
    stopper = stopper or FakeStopper()
    launcher, said = FakeLauncher(), []
    command = RetryCommand(
        stopper=stopper,
        launcher=launcher,
        open_app=resources.opener(),
        echo=said.append,
    )
    return command, stopper, launcher, said


async def _run(command: RetryCommand, **overrides: Any) -> None:
    options: dict[str, Any] = {
        "max_attempts": 10,
        "keep_workers": False,
        "start_worker": False,
        "worker_args": (),
        "log": None,
        "grace_seconds": 5.0,
        "dry_run": False,
    }
    await command.run(PROJECT, **{**options, **overrides})


@pytest.mark.asyncio
async def test_it_stops_workers_and_grants_attempts_on_each_exhausted_gate() -> None:
    first, second = _gate(), _gate()
    resources = FakeResources([first, second])
    command, stopper, launcher, said = _command(resources)

    await _run(command)

    assert stopper.stopped
    assert [(g, p) for g, p, _, _ in resources.answered] == [
        (first.gate_id, {"max_attempts": 10}),
        (second.gate_id, {"max_attempts": 10}),
    ]
    # A named, labelled request: running it twice answers each gate once.
    gate_id, _, by, request_id = resources.answered[0]
    assert by == "vibey retry" and request_id == f"retry-{gate_id}-10"
    assert launcher.started == []
    assert any("no worker started" in line for line in said)


@pytest.mark.asyncio
async def test_a_gate_that_is_a_decision_is_named_never_answered() -> None:
    exhausted, review = _gate(), _gate("review")
    resources = FakeResources([exhausted, review])
    command, _, _, said = _command(resources)

    await _run(command)

    assert [g for g, *_ in resources.answered] == [exhausted.gate_id]
    assert any(f"vibey gates {PROJECT}" in line and "1 other" in line for line in said)


@pytest.mark.asyncio
async def test_with_nothing_exhausted_it_says_so() -> None:
    resources = FakeResources([])
    command, _, _, said = _command(resources)

    await _run(command)

    assert resources.answered == []
    assert any("no exhausted-attempts gate is open" in line for line in said)


@pytest.mark.asyncio
async def test_keep_workers_leaves_the_running_workers_alone() -> None:
    command, stopper, _, _ = _command(FakeResources([_gate()]))

    await _run(command, keep_workers=True)

    assert not stopper.planned and not stopper.stopped


@pytest.mark.asyncio
async def test_a_worker_that_survives_means_no_gate_is_answered() -> None:
    resources = FakeResources([_gate()])
    command, _, _, _ = _command(resources, FakeStopper(survivors=(200,)))

    with pytest.raises(typer.Exit) as caught:
        await _run(command)

    assert caught.value.exit_code == 1
    assert resources.answered == []  # a live worker still holds its leases


@pytest.mark.asyncio
async def test_an_unknown_project_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    command, stopper, _, _ = _command(FakeResources([], known=False))

    with pytest.raises(typer.Exit) as caught:
        await _run(command)

    assert caught.value.exit_code == 1
    assert f"unknown project {PROJECT}" in capsys.readouterr().err
    assert not stopper.planned


@pytest.mark.asyncio
async def test_start_worker_runs_it_for_this_project_with_the_arguments_after_dashes(
    tmp_path: Path,
) -> None:
    command, _, launcher, said = _command(FakeResources([_gate()]))
    log = tmp_path / "w.log"

    await _run(
        command,
        start_worker=True,
        worker_args=("--engines", "gptossloop", "--auto-answer"),
        log=log,
    )

    assert launcher.started == [
        (["worker", "--project", str(PROJECT), "--engines", "gptossloop", "--auto-answer"], log)
    ]
    assert any("pid 777" in line and str(log) in line for line in said)


@pytest.mark.asyncio
async def test_an_explicit_project_in_the_worker_arguments_is_not_doubled() -> None:
    command, _, launcher, _ = _command(FakeResources([]))

    await _run(command, start_worker=True, worker_args=("--project", str(PROJECT)))

    assert launcher.started[0][0] == ["worker", "--project", str(PROJECT)]
    assert launcher.started[0][1].name == f"worker-{str(PROJECT)[:8]}.log"  # the default log


@pytest.mark.asyncio
async def test_a_dry_run_changes_nothing_and_says_what_it_would_do() -> None:
    resources = FakeResources([_gate()])
    command, stopper, launcher, said = _command(resources)

    await _run(command, dry_run=True, start_worker=True)

    assert resources.answered == [] and launcher.started == []
    assert not stopper.stopped
    text = "\n".join(said)
    assert "would grant 10 attempts" in text and "would start: vibey worker" in text


def test_the_command_passes_its_options_and_the_arguments_after_dashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    class Recorder:
        async def run(self, project_id: UUID, **kwargs: Any) -> None:
            seen.update(project_id=project_id, **kwargs)

    monkeypatch.setattr(cli_main, "RETRY", Recorder())

    result = CliRunner().invoke(
        cli_main.app,
        [
            "retry",
            str(PROJECT),
            "--max-attempts",
            "12",
            "--start-worker",
            "--",
            "--engines",
            "gptossloop",
        ],
    )

    assert result.exit_code == 0, result.output
    assert seen["project_id"] == PROJECT and seen["max_attempts"] == 12
    assert seen["start_worker"] is True and seen["keep_workers"] is False
    assert seen["worker_args"] == ("--engines", "gptossloop")
