# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A dead letter's whole path through the production code (ADR-0056): the reaper parks
it, a person answers the gate, and the full worker's dispatcher settles it. Real
Postgres; the in-memory bus the composition root builds when no broker is configured."""

import os
from pathlib import Path

import asyncpg
import pytest

from vibey.bootstrap import build_app, build_full_worker, database_url
from vibey.domain.job import JobState
from vibey.domain.queue_reap import DeadLetter, ReapAction, ReapCondition, ReapVerdict
from vibey.infrastructure.bus.in_memory import InMemoryBus
from vibey.infrastructure.db.queue_reap_store import PostgresQueueReapStore
from vibey.infrastructure.engines.scripted_decompose import ScriptedWorkPlanProducer
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider

pytestmark = pytest.mark.system


@pytest.fixture(autouse=True)
async def _use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/vibey_test",
    )
    monkeypatch.setenv("VIBEY_PG_URL", url)
    conn = await asyncpg.connect(database_url())
    await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
    await conn.close()


@pytest.mark.parametrize(("choice", "replayed"), [("replay", True), ("dismiss", False)])
async def test_a_parked_dead_letter_is_settled_by_its_answer(
    tmp_path: Path, choice: str, replayed: bool
) -> None:
    item = DeadLetter(
        queue="vibey.jobs.dlq",
        origin_queue="vibey.jobs",
        reason="rejected",
        body='{"job_id": "x"}',
        message_id="m1",
    )
    verdict = ReapVerdict(
        subject=item.identity,
        queue=item.queue,
        condition=ReapCondition.DEAD_LETTERED,
        measured=1.0,
        threshold=1.0,
        unit="messages",
        action=ReapAction.PARK,
    )
    async with build_app() as resources:
        project = await resources.projects.create(
            "dead-letters", tmp_path, max_cycles=3, config={"project": {"name": "dead-letters"}}
        )
        pool = await asyncpg.create_pool(database_url(), min_size=1, max_size=2)
        try:
            job_id = await PostgresQueueReapStore(pool).park_dead_letter(
                project.project_id, item, verdict
            )
        finally:
            await pool.close()
        assert job_id is not None

        worker = build_full_worker(
            resources=resources,
            project=project,
            design_provider=ScriptedDesignProvider(),
            visual_provider=ScriptedVisualProvider(),
            decomposer=ScriptedWorkPlanProducer(),
            owner="w",
        )
        # Parked: no worker takes it, and none waits on it.
        assert await worker.run_once(project.project_id) is False

        (gate,) = await resources.gates.open_for_project(project.project_id)
        assert gate.kind == "bus_dead_lettered"
        await resources.gates.answer(gate.gate_id, answer={"choice": choice}, answered_by="op")
        assert await worker.run_once(project.project_id) is True

        job = await resources.jobs.get(job_id)
        assert job is not None and job.state is JobState.SUCCEEDED
        bus = resources.bus
        assert isinstance(bus, InMemoryBus)
        depths = {d.queue: d.ready for d in await bus.depths()}
        assert depths.get("vibey.jobs", 0) == (1 if replayed else 0)
