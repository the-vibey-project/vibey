# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition root wires hybrid engine dispatch per project (ADR-0079)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from vibey import __version__
from vibey.application.dto import ProjectRecord
from vibey.application.engine_dispatch_service import EngineDispatchService
from vibey.bootstrap import _engine_dispatch
from vibey.domain.engine import EngineId
from vibey.domain.phase import Phase

NOW = datetime(2026, 10, 3, tzinfo=UTC)


def _project(config: dict[str, object]) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/w/p"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config=config,
        created_at=NOW,
        updated_at=NOW,
    )


def _adapters(*engines: EngineId) -> dict[EngineId, Any]:
    return {engine: object() for engine in engines}


def test_resources_without_a_store_keep_todays_selection() -> None:
    resources: Any = SimpleNamespace(clock=object())
    assert _engine_dispatch(resources, _project({}), (EngineId.GPTOSSLOOP,), {}, None) is None


def test_a_store_wires_the_projects_dispatch_over_the_workers_pool() -> None:
    resources: Any = SimpleNamespace(clock=object(), engine_dispatch_store=object())
    service = _engine_dispatch(
        resources,
        _project({"engines": {"mode": "hybrid", "paid_daily_cap": 2}}),
        (EngineId.GPTOSSLOOP, EngineId.QWENLOOP),
        _adapters(EngineId.GPTOSSLOOP, EngineId.QWENLOOP, EngineId.CLAUDELOOP),
        frozenset({EngineId.GPTOSSLOOP, EngineId.CLAUDELOOP}),
        environ={"VIBEY_ENGINES_PAID_DAILY_CAP": "1"},
    )
    assert isinstance(service, EngineDispatchService)
    assert service._local_engines == (EngineId.GPTOSSLOOP,)
    assert service._config.mode == "hybrid" and service._config.paid_daily_cap == 1
    assert service._implementation == f"vibey-engine {__version__}"


def test_with_no_allow_list_every_configured_local_engine_is_in_the_pool() -> None:
    resources: Any = SimpleNamespace(clock=object(), engine_dispatch_store=object())
    service = _engine_dispatch(
        resources,
        _project({}),
        (EngineId.GPTOSSLOOP, EngineId.QWENLOOP),
        _adapters(EngineId.GPTOSSLOOP),
        None,
        environ={},
    )
    assert service is not None and service._local_engines == (EngineId.GPTOSSLOOP,)
