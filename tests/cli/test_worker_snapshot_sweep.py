# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker` sweeps old run snapshots once as it starts (SP-LOOPS Phase 4, Task 8; R10).

A run's snapshot folder is removed when its BUILD run ends; one a crashed worker left behind is
removed by the next worker's sweep, past an age no session can reach. A sweep that cannot run is
logged and never stops the worker. No database is reached: the worker's event loop is replaced.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

import vibey.bootstrap
import vibey.cli.main as main
from vibey.application.dto import PruneReport
from vibey.domain.config import ConfigError

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


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


def _serving(monkeypatch: pytest.MonkeyPatch, outcome: PruneReport | Exception) -> None:
    monkeypatch.setattr(
        vibey.bootstrap, "loop_capabilities_service", lambda *a, **k: _Service(outcome)
    )


def test_a_sweep_logs_what_it_removed_and_names_what_it_left(
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

    main._sweep_loop_snapshots(logger)  # noqa: SLF001

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
def test_a_sweep_that_cannot_run_is_logged_never_fatal(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    _serving(monkeypatch, error)
    logger = _Logger()

    main._sweep_loop_snapshots(logger)  # noqa: SLF001

    assert logger.lines == [("warning", "loop_snapshot_sweep_refused", {"error": str(error)})]


def test_the_worker_sweeps_once_before_its_loop_starts(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    monkeypatch.setattr(main, "_sweep_loop_snapshots", lambda logger: order.append("sweep"))

    def run(coroutine: Coroutine[Any, Any, Any]) -> None:
        order.append("run_worker")
        coroutine.close()

    monkeypatch.setattr(asyncio, "run", run)

    result = runner.invoke(main.app, ["worker", "--once"])

    assert result.exit_code == 0, result.output
    assert order == ["sweep", "run_worker"]
