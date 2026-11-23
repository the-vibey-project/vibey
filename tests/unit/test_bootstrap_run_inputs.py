# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition of run inputs in `bootstrap.py` (SP-LOOPS Phase 3, fix round 2: N2, N7).

`vibey inputs` (through `run_inputs_app`) and the worker (through `build_full_worker`) both build
the service with `run_inputs_service`, whose store root is `run_inputs_root()`: the one
`UserStateFolder` path, so the two can never disagree about where inputs live. The worker's
limits are `run_inputs_limits`, the person's own `[inputs]`, never the defaults. Nothing here
reads the real home folder's config or state: both are stand-ins under pytest's folder.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from platformdirs import user_state_path

import vibey.bootstrap as bootstrap
from vibey.application.dto import ProjectRecord
from vibey.application.run_inputs_service import RunInputsService
from vibey.domain.config import ConfigError
from vibey.domain.phase import Phase
from vibey.domain.run_input import RunInputsSettings
from vibey.infrastructure.user_state_folder import UserStateFolder

AT = datetime(2026, 11, 23, tzinfo=UTC)


def test_the_store_root_is_the_persons_state_folder_inputs() -> None:
    assert bootstrap.run_inputs_root() == UserStateFolder(user_state_path).inputs()


def test_the_worker_limits_are_the_persons_own_inputs_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "vibey.toml"
    monkeypatch.setattr(bootstrap, "acp_user_config", lambda: config)
    assert bootstrap.run_inputs_limits() == RunInputsSettings()  # no file: no declaration
    config.write_text("[inputs]\nmax_items = 3\nmax_prompt_bytes = 1024\n")
    assert bootstrap.run_inputs_limits() == RunInputsSettings(max_items=3, max_prompt_bytes=1024)
    config.write_text("[inputs]\nmax_items = 0\n")
    with pytest.raises(ConfigError, match="max_items"):
        bootstrap.run_inputs_limits()


class _Clock:
    def now(self) -> datetime:
        return AT


class _Ledger:
    def __init__(self) -> None:
        self.drafts: list[Any] = []

    async def append(self, draft: Any) -> None:
        self.drafts.append(draft)


def _resources(tmp_path: Path) -> tuple[Any, UUID]:
    project_id = uuid4()
    record = ProjectRecord(
        project_id=project_id,
        name="greeter",
        repo_path=tmp_path / "repo",
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=AT,
        updated_at=AT,
    )

    class _Projects:
        async def get(self, wanted: UUID) -> ProjectRecord | None:
            return record if wanted == project_id else None

    return SimpleNamespace(clock=_Clock(), projects=_Projects(), ledger=_Ledger()), project_id


def test_the_service_stores_under_run_inputs_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "state" / "inputs"
    monkeypatch.setattr(bootstrap, "run_inputs_root", lambda: root)
    resources, project_id = _resources(tmp_path)
    service = bootstrap.run_inputs_service(resources, RunInputsSettings)
    item = asyncio.run(service.add(project_id, "paste", "paste", b"words"))
    assert (root / str(project_id) / "objects" / item.digest[:2] / item.digest).is_file()
    assert len(resources.ledger.drafts) == 1


def test_vibey_inputs_composes_through_run_inputs_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources, _ = _resources(tmp_path)
    calls: list[tuple[Any, Callable[[], RunInputsSettings]]] = []

    @asynccontextmanager
    async def fake_app() -> AsyncIterator[Any]:
        yield resources

    def recording(given: Any, limits: Callable[[], RunInputsSettings]) -> RunInputsService:
        calls.append((given, limits))
        return RunInputsService.__new__(RunInputsService)

    monkeypatch.setattr(bootstrap, "build_app", fake_app)
    monkeypatch.setattr(bootstrap, "run_inputs_service", recording)
    settings = RunInputsSettings(max_items=2)

    async def open_it() -> None:
        async with bootstrap.run_inputs_app(settings):
            pass

    asyncio.run(open_it())
    [(given, limits)] = calls
    assert given is resources
    assert limits() == settings
