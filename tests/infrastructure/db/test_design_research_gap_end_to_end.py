# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""DESIGN research with no evidence, on the real queue and ledger: gate, or recorded gap.

Observed live on 2026-09-29 (project 9692abab, issue #998): every delivery on the sovereign
provider parked at a `research_evidence` gate in DESIGN, because a local model has no web
access and the provider rightly refuses to invent a source. This pins both declared
answers end to end, through the real queue, the real ledger and the real sovereign
provider's refusal: `gate` (the default) still waits for a person, and `record_gap` lets
DESIGN finish with every topic recorded as not researched -- on the ledger and in the
published spec -- and no source invented anywhere.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg

from vibey.application.design_research_handler import (
    RESEARCH_EVIDENCE_GATE_KIND,
    DesignResearchHandler,
)
from vibey.application.design_synthesis_handler import DesignSpecHandler, DesignSynthesizeHandler
from vibey.application.dto import EnqueueRequest
from vibey.application.job_dispatcher import JobDispatcher
from vibey.application.worker import WorkerLoop
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState, idempotency_key
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.domain.research_gap import ResearchOnUnavailable
from vibey.infrastructure.db.design_ledger import PostgresDesignLedger
from vibey.infrastructure.db.design_spec_repository import FileDesignSpecRepository
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.project_repository import PostgresProjectRepository
from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider

TOPICS = ("prior-art", "libraries", "api-docs")


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 29, tzinfo=UTC)


async def _design_after_the_interview(
    pool: asyncpg.Pool, repo: Path, policy: ResearchOnUnavailable
) -> tuple[UUID, PostgresJobRepository, PostgresHumanGateRepository, WorkerLoop]:
    """A project in DESIGN whose interview is done: its research, synthesis and spec jobs
    queued as the interview handler queues them, and a worker to run them."""
    projects = PostgresProjectRepository(pool)
    project = await projects.create("research-gaps", repo, max_cycles=10, config={})
    project = await projects.transition(project.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)
    project_id = project.project_id
    jobs = PostgresJobRepository(pool)
    gates = PostgresHumanGateRepository(pool)
    ledger = PostgresDesignLedger(PostgresLedgerRepository(pool))
    research = [
        await jobs.enqueue(
            EnqueueRequest(
                project_id=project_id,
                cycle=1,
                phase=Phase.DESIGN,
                kind="design.research",
                idempotency_key=idempotency_key(project_id, 1, "design.research", topic),
                payload={"topic": topic},
            )
        )
        for topic in TOPICS
    ]
    synth = await jobs.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.DESIGN,
            kind="design.synthesize",
            idempotency_key=idempotency_key(project_id, 1, "design.synthesize", "spec"),
            depends_on=tuple(job.id for job in research),
        )
    )
    await jobs.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.DESIGN,
            kind="design.spec",
            idempotency_key=idempotency_key(project_id, 1, "design.spec", "final"),
            depends_on=(synth.id,),
        )
    )
    specs = FileDesignSpecRepository(projects)
    # The real sovereign provider, with no evidence directory: it refuses every topic
    # before any model is asked. Synthesis is scripted, since that is not under test.
    researcher = GptossloopDesignProvider(evidence_dir=None)
    dispatcher = JobDispatcher(
        {
            "design.research": DesignResearchHandler(
                ledger=ledger,
                researcher=researcher,
                clock=FixedClock(),
                engine_id=researcher.engine_id,
                on_unavailable=policy,
            ),
            "design.synthesize": DesignSynthesizeHandler(
                ledger=ledger, synthesizer=ScriptedDesignProvider(), specs=specs
            ),
            "design.spec": DesignSpecHandler(specs=specs),
        }
    )
    worker = WorkerLoop(jobs=jobs, gates=gates, handler=dispatcher, owner="design-worker")
    return project_id, jobs, gates, worker


async def test_by_default_design_research_with_no_evidence_waits_for_a_person(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    project_id, _, _, worker = await _design_after_the_interview(
        migrated_pool, tmp_path, ResearchOnUnavailable.GATE
    )
    while await worker.run_once(project_id):
        pass

    async with migrated_pool.acquire() as conn:
        states = {
            row["kind"]: row["state"]
            for row in await conn.fetch(
                "SELECT kind, state FROM job WHERE project_id = $1", project_id
            )
        }
        gate_kinds = [
            row["kind"]
            for row in await conn.fetch(
                "SELECT kind FROM human_gate WHERE project_id = $1", project_id
            )
        ]
    assert states["design.research"] == JobState.AWAITING_HUMAN.value
    assert states["design.synthesize"] != JobState.SUCCEEDED.value
    assert gate_kinds == [RESEARCH_EVIDENCE_GATE_KIND] * len(TOPICS)
    assert not (tmp_path / ".vibey/context/spec.md").exists()


async def test_record_gap_finishes_design_and_the_spec_states_every_gap(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    project_id, _, _, worker = await _design_after_the_interview(
        migrated_pool, tmp_path, ResearchOnUnavailable.RECORD_GAP
    )
    ran = 0
    while await worker.run_once(project_id):
        ran += 1
    assert ran == len(TOPICS) + 2  # three research jobs, the synthesis, the spec

    async with migrated_pool.acquire() as conn:
        states = await conn.fetch("SELECT state FROM job WHERE project_id = $1", project_id)
        gates = await conn.fetchval(
            "SELECT count(*) FROM human_gate WHERE project_id = $1", project_id
        )
    assert {row["state"] for row in states} == {JobState.SUCCEEDED.value}
    assert gates == 0

    events = await PostgresLedgerRepository(migrated_pool).all_for_project(project_id)
    recorded = [event for event in events if event.kind is EventKind.RESEARCH_GAP_RECORDED]
    assert sorted(str(event.payload["topic"]) for event in recorded) == sorted(TOPICS)
    assert all(event.provenance is Provenance.TRUSTED for event in recorded)
    assert all(event.engine_id is EngineId.GPTOSSLOOP for event in recorded)
    assert all("VIBEY_EVIDENCE_DIR is unset" in str(event.payload["reason"]) for event in recorded)
    # Nothing that looks like research was written: no source anywhere on the ledger.
    assert not [event for event in events if event.kind is EventKind.ARTIFACT_PRODUCED]
    assert not [event for event in events if "source" in event.payload]

    spec_md = (tmp_path / ".vibey/context/spec.md").read_text()
    assert "## Research not performed" in spec_md
    for topic in TOPICS:
        assert f"- {topic}: not researched. " in spec_md
    open_items = (tmp_path / ".vibey/context/open-items.md").read_text()
    assert open_items.count("Research not performed -- ") == len(TOPICS)
