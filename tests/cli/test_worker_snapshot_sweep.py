# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker` sweeps old run snapshots once as it starts (SP-LOOPS Phase 4, Task 8; R10).

A run's snapshot folder is removed when its BUILD run ends; one a crashed worker left behind is
removed by the next worker's sweep, past an age no session can reach: the longest run deadline
any registered project can use, plus an hour, or the person's `snapshot_max_age_days`, whichever
is longer. A sweep that cannot run is logged and never stops the worker. No database is reached:
the projects come from a stand-in store. That the worker sweeps before it claims anything is
pinned against a real database in `test_worker_all_projects.py`.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

import vibey.bootstrap
import vibey.cli.main as main
from vibey.application.dto import ProjectRecord, PruneReport
from vibey.bootstrap import ENGINE_RUN_MINUTES_ENV, LOOPS_STORE, loop_capabilities_service
from vibey.domain.config import ConfigError
from vibey.domain.phase import Phase


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _Logger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("error", event, kwargs))


class _Service:
    def __init__(self, outcome: PruneReport | Exception) -> None:
        self.outcome = outcome

    def sweep(self) -> PruneReport:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class _Projects:
    """The one `ProjectReader` call the sweep makes: every registered project."""

    def __init__(self, *configs: Mapping[str, object], fails: Exception | None = None) -> None:
        self.configs = configs
        self.fails = fails

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        if self.fails is not None:
            raise self.fails
        now = datetime.now(UTC)
        return tuple(
            ProjectRecord(
                project_id=uuid4(),
                name=f"p{index}",
                repo_path=Path("/repo"),
                phase=Phase.INTAKE,
                cycle=1,
                max_cycles=1,
                config=config,
                created_at=now,
                updated_at=now,
            )
            for index, config in enumerate(self.configs)
        )


def _serving(monkeypatch: pytest.MonkeyPatch, outcome: PruneReport | Exception) -> None:
    monkeypatch.setattr(
        vibey.bootstrap, "loop_capabilities_service", lambda *a, **k: _Service(outcome)
    )


async def test_a_sweep_logs_what_it_removed_and_names_what_it_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serving(
        monkeypatch,
        PruneReport(
            (Path("/s/run-old"),),
            ((Path("/s/run-link"), "is a symlink; it is never followed or removed"),),
        ),
    )
    logger = _Logger()

    await main._sweep_loop_snapshots(logger, _Projects())  # noqa: SLF001

    assert logger.lines == [
        ("info", "loop_snapshot_sweep", {"removed": 1, "refused": 1}),
        (
            "warning",
            "loop_snapshot_left",
            {"path": "/s/run-link", "reason": "is a symlink; it is never followed or removed"},
        ),
    ]


@pytest.mark.parametrize(
    "error",
    [
        ConfigError("/person/vibey.toml", "loops.snapshot_max_age_days must be at least 1"),
        PermissionError("the snapshot folder cannot be listed"),
        ValueError("the age must be at least 0 seconds"),
    ],
    ids=["config", "os", "value"],
)
async def test_a_sweep_that_cannot_run_is_logged_never_fatal(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    _serving(monkeypatch, error)
    logger = _Logger()

    await main._sweep_loop_snapshots(logger, _Projects())  # noqa: SLF001

    assert logger.lines == [("warning", "loop_snapshot_sweep_refused", {"error": str(error)})]


async def test_projects_that_cannot_be_listed_mean_no_sweep_at_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without every project's deadline the age could be too short for a live run, so the
    sweep is skipped and said, and the worker goes on: a run's own folder still goes when the
    run ends."""

    def never(*args: object, **kwargs: object) -> object:
        raise AssertionError("no service is built without the projects' deadlines")

    monkeypatch.setattr(vibey.bootstrap, "loop_capabilities_service", never)
    logger = _Logger()
    failure = ConnectionError("the database is unreachable")

    await main._sweep_loop_snapshots(logger, _Projects(fails=failure))  # noqa: SLF001

    assert logger.lines == [("warning", "loop_snapshot_sweep_refused", {"error": str(failure)})]


async def test_a_deadline_that_cannot_be_computed_means_no_sweep_never_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security finding (DoS): the deadline was computed outside the guard, so an overflow in
    a person-set `max_run_minutes` crashed the worker at start-up. Any arithmetic failure in
    the deadline is now a refused sweep, logged, and the worker goes on."""
    failure = OverflowError("date value out of range")

    def overflowing(*args: object, **kwargs: object) -> timedelta:
        raise failure

    def never(*args: object, **kwargs: object) -> object:
        raise AssertionError("no service is built without a deadline")

    monkeypatch.setattr(vibey.bootstrap, "longest_engine_run_deadline", overflowing)
    monkeypatch.setattr(vibey.bootstrap, "loop_capabilities_service", never)
    logger = _Logger()

    await main._sweep_loop_snapshots(  # noqa: SLF001
        logger, _Projects({"engines": {"max_run_minutes": 10**15}})
    )

    assert logger.lines == [("warning", "loop_snapshot_sweep_refused", {"error": str(failure)})]


def _aged(folder: Path, hours: float) -> Path:
    folder.mkdir(parents=True)
    (folder / "plugin.json").write_text("{}", encoding="utf-8")
    then = time.time() - hours * 3600
    for path in (folder / "plugin.json", folder):
        os.utime(path, (then, then))
    return folder


@pytest.mark.parametrize(
    ("configs", "kept"),
    [((), False), (({"engines": {"max_run_minutes": 2880}}, {}), True)],
    ids=["default-deadline", "a-project-runs-two-days"],
)
async def test_a_project_deadline_longer_than_the_default_keeps_its_live_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    configs: tuple[Mapping[str, object], ...],
    kept: bool,
) -> None:
    """Review finding 2: the person's one day against a project's two-day `[engines]
    max_run_minutes`. A 30-hour-old folder is past the default cutoff (one day, as 240 minutes
    and an hour is shorter) but inside the project's (two days and an hour), so it may be a live
    session's and stays; a 50-hour-old one is past both and goes. Under the default alone, the
    30-hour folder goes too, so the test is not vacuous."""
    monkeypatch.delenv(ENGINE_RUN_MINUTES_ENV, raising=False)
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()
    person.write_text("[loops]\nsnapshot_max_age_days = 1\n", encoding="utf-8")

    def composed(run_deadline: timedelta | None = None, **kwargs: object) -> object:
        return loop_capabilities_service(run_deadline, user_config=person)

    monkeypatch.setattr(vibey.bootstrap, "loop_capabilities_service", composed)
    snapshots = person.parent / LOOPS_STORE / "snapshots"
    live = _aged(snapshots / "run-live", hours=30)
    dead = _aged(snapshots / "run-dead", hours=50)
    logger = _Logger()

    await main._sweep_loop_snapshots(logger, _Projects(*configs))  # noqa: SLF001

    assert live.exists() is kept
    assert not dead.exists()
    removed = 1 if kept else 2
    assert logger.lines == [("info", "loop_snapshot_sweep", {"removed": removed, "refused": 0})]
