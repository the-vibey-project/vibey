# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The worker gives BUILD runs their inputs through the same composition `vibey inputs` uses
(SP-LOOPS Phase 3, fix round 2: N2, N7).

`build_full_worker` must build its run inputs service with `run_inputs_service` -- the one whose
store root is `run_inputs_root()` -- and with `run_inputs_limits`, the person's own `[inputs]`.
Reverting either (another root, or `RunInputsSettings()` defaults) fails here.
"""

import asyncio
import os
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import asyncpg
import pytest

import vibey.bootstrap as bootstrap
from tests.db_roles import TestDatabaseRoles
from vibey.application.run_inputs_service import RunInputsService
from vibey.domain.run_input import RunInputsSettings
from vibey.infrastructure.engines.scripted_decompose import ScriptedWorkPlanProducer
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider

pytestmark = pytest.mark.system
ROLES = TestDatabaseRoles.from_environ(os.environ)


@pytest.fixture(autouse=True)
def _an_empty_schema_the_application_role_runs_on(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]

    async def fresh() -> None:
        conn = await asyncpg.connect(owner)
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.execute("CREATE SCHEMA public")
        finally:
            await conn.close()
        await ROLES.restore(owner, bootstrap.migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(owner))


async def test_the_worker_composes_run_inputs_with_the_shared_root_and_live_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Any, Callable[[], RunInputsSettings]]] = []
    real = bootstrap.run_inputs_service

    def recording(resources: Any, limits: Callable[[], RunInputsSettings]) -> RunInputsService:
        calls.append((resources, limits))
        return real(resources, limits)

    monkeypatch.setattr(bootstrap, "run_inputs_service", recording)
    monkeypatch.setattr(bootstrap, "run_inputs_root", lambda: tmp_path / "state" / "inputs")
    async with bootstrap.build_app() as resources:
        project = await resources.projects.create("wired", tmp_path, max_cycles=3, config={})
        bootstrap.build_full_worker(
            resources=resources,
            project=project,
            design_provider=ScriptedDesignProvider(),
            visual_provider=ScriptedVisualProvider(),
            decomposer=ScriptedWorkPlanProducer(),
            owner="inputs-wiring",
            engine_adapters={},
        )
    [(given, limits)] = calls
    assert given is resources
    assert limits is bootstrap.run_inputs_limits


async def test_the_worker_composes_the_snapshot_beside_the_inputs_with_the_projects_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUILD's run inputs and its capability snapshot (SP-LOOPS Phase 4, Task 8) coexist: the
    worker composes both, the snapshot with the deadline the project's own sessions run under,
    so a sweep never takes a snapshot a session inside its deadline still holds (R10)."""
    deadlines: list[Any] = []
    inputs: list[Any] = []
    real = bootstrap.loop_capabilities_service
    real_inputs = bootstrap.run_inputs_service

    def recording(run_deadline: Any = None, **kwargs: Any) -> Any:
        deadlines.append(run_deadline)
        return real(run_deadline, **kwargs)

    def recording_inputs(resources: Any, limits: Any) -> RunInputsService:
        inputs.append(resources)
        return real_inputs(resources, limits)

    monkeypatch.delenv(bootstrap.ENGINE_RUN_MINUTES_ENV, raising=False)
    monkeypatch.setattr(bootstrap, "loop_capabilities_service", recording)
    monkeypatch.setattr(bootstrap, "run_inputs_service", recording_inputs)
    monkeypatch.setattr(bootstrap, "run_inputs_root", lambda: tmp_path / "state" / "inputs")
    async with bootstrap.build_app() as resources:
        project = await resources.projects.create(
            "wired", tmp_path, max_cycles=3, config={"engines": {"max_run_minutes": 90}}
        )
        bootstrap.build_full_worker(
            resources=resources,
            project=project,
            design_provider=ScriptedDesignProvider(),
            visual_provider=ScriptedVisualProvider(),
            decomposer=ScriptedWorkPlanProducer(),
            owner="snapshot-wiring",
            engine_adapters={},
        )
    assert inputs == [resources]
    assert deadlines == [timedelta(minutes=90)]
