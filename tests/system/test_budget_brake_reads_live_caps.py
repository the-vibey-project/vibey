# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A cap `vibey budget set` writes binds the next BUILD session of a worker already running.

`bootstrap.build_full_worker` is the composition `vibey worker` runs, and it is built
once, when the worker starts. The project here is created with no cap, the worker is
built, and only then is a cap set -- below what the cycle has already spent. The next
`build.implement` the worker claims must park a `budget_exhausted` gate before any
engine session starts, which is what `vibey budget set` tells the person it will do.
"""

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
import pytest

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import EnqueueRequest
from vibey.bootstrap import build_app, build_full_worker, migrations_dir
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState, idempotency_key
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID
from vibey.infrastructure.engines.scripted import ScriptedEngine
from vibey.infrastructure.engines.scripted_decompose import ScriptedWorkPlanProducer
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider
from vibey.infrastructure.engines.tailer import LedgerEventDraft

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
        await ROLES.restore(owner, migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(owner))


async def test_a_worker_started_uncapped_parks_its_next_session_once_a_cap_is_set(
    tmp_path: Path,
) -> None:
    async with build_app() as resources:
        project = await resources.projects.create("brake", tmp_path, max_cycles=3, config={})
        pid = project.project_id
        payload: dict[str, object] = {"cost_usd": 3.21}
        await resources.ledger.append(
            LedgerEventDraft(
                project_id=pid,
                cycle=project.cycle,
                phase=Phase.BUILD,
                kind=EventKind.TURN_COMPLETED,
                engine_id=EngineId.CLAUDELOOP,
                job_id=None,
                causation_id=None,
                correlation_id=pid,
                provenance=Provenance.AGENT,
                produced_at=datetime.now(UTC),
                payload=payload,
                digest=digest_event(payload),
            )
        )
        adapters = {
            engine_id: ScriptedEngine(descriptor=descriptor, base_dir=tmp_path / engine_id.value)
            for engine_id, descriptor in BY_ENGINE_ID.items()
        }
        for engine_id, adapter in adapters.items():
            await resources.engine_health_service.update_from_preflight(
                pid, engine_id, await adapter.preflight(), conformance_ok=True
            )
        # Built as `vibey worker` builds it, while the project has no cap at all.
        worker = build_full_worker(
            resources=resources,
            project=project,
            design_provider=ScriptedDesignProvider(),
            visual_provider=ScriptedVisualProvider(),
            decomposer=ScriptedWorkPlanProducer(),
            owner="budget-worker",
            engine_adapters=adapters,
        )

        change = await resources.project_budgets.set_caps(pid, max_dollars=2.0, by="test")
        job = await resources.jobs.enqueue(
            EnqueueRequest(
                project_id=pid,
                cycle=project.cycle,
                phase=Phase.BUILD,
                kind="build.implement",
                idempotency_key=idempotency_key(pid, project.cycle, "build.implement", "item-1"),
                work_item_id="item-1",
                payload={"title": "greet", "base_ref": "HEAD"},
                requirement={"effort": "medium"},
            )
        )

        assert change.after.exhausted is True
        assert await worker.run_once(pid) is True

        parked = await resources.jobs.get(job.id)
        gates = await resources.gates.open_for_project(pid)

    assert parked is not None and parked.state is JobState.AWAITING_HUMAN
    assert [gate.kind for gate in gates] == ["budget_exhausted"]
    assert "$3.21 spent of $2.00 cap" in gates[0].prompt
