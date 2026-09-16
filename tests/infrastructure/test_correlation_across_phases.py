# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every event of one delivery carries one correlation id.

Issue #89's first acceptance criterion, driven through the real write paths:
``PostgresDesignLedger``, ``run_and_record`` + ``PostgresBuildLedger``, and
``PostgresReviewLedger``. Those are the three adapters that used to call
``uuid4()``, so this fails the moment any of them goes back to minting.

The repository is a fake that collects drafts -- the assertion is about what
the adapters put on a draft, which is decided before Postgres is involved.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from tests.application.fakes import make_job
from vibey.application.build_engine_run import run_and_record
from vibey.application.design import DesignEvent
from vibey.application.dto import EngineEvent, RunHandle
from vibey.domain.correlation import DeliveryCorrelation
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.build_ledger import PostgresBuildLedger
from vibey.infrastructure.db.design_ledger import PostgresDesignLedger
from vibey.infrastructure.db.review_ledger import PostgresReviewLedger
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.tailer import LedgerEventDraft

NOW = datetime(2026, 9, 15, tzinfo=UTC)


class _CollectingRepository:
    """Stands in for PostgresLedgerRepository: append() is all these
    adapters use, and the ids are set before the row ever exists."""

    def __init__(self) -> None:
        self.drafts: list[LedgerEventDraft] = []

    async def append(self, draft: LedgerEventDraft) -> None:
        self.drafts.append(draft)


class _ScriptedEngine:
    descriptor = CLAUDELOOP

    async def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]:
        yield EngineEvent(
            kind=EventKind.VERDICT_RENDERED.value,
            at=NOW,
            payload={"complete": True, "remaining_work": []},
        )


def _handle(run_id: UUID) -> RunHandle:
    return RunHandle(
        run_id=run_id,
        engine_id=CLAUDELOOP.engine_id,
        run_dir=Path("/tmp/unused"),
        pid=None,
    )


async def _write_one_delivery(repository: Any, project_id: UUID, run_id: UUID) -> None:
    await PostgresDesignLedger(repository).append(
        project_id,
        1,
        uuid4(),
        None,
        DesignEvent(
            kind=EventKind.DECISION_RECORDED,
            provenance=Provenance.TRUSTED,
            produced_at=NOW,
            payload={"decision_id": "d1", "title": "t", "choice": "c"},
        ),
    )

    # BUILD, cycle 1 -- through the shared run driver, exactly as the
    # implement and verify handlers reach it.
    await run_and_record(
        _ScriptedEngine(),  # type: ignore[arg-type]
        PostgresBuildLedger(repository),
        job=make_job(project_id),
        handle=_handle(run_id),
    )

    # REVIEW, cycle 7 -- the loop-back has moved the cycle on six times.
    await PostgresReviewLedger(repository).append_event(
        project_id,
        7,
        uuid4(),
        EventKind.VERDICT_RENDERED,
        {"complete": True},
    )


async def test_design_build_and_review_share_one_correlation_id() -> None:
    project_id = uuid4()
    repository = _CollectingRepository()

    await _write_one_delivery(repository, project_id, uuid4())

    expected = DeliveryCorrelation().for_project(project_id).value
    assert {draft.phase for draft in repository.drafts} == {
        Phase.DESIGN,
        Phase.BUILD,
        Phase.REVIEW,
    }
    assert {draft.correlation_id for draft in repository.drafts} == {expected}


async def test_a_second_delivery_gets_a_different_id() -> None:
    """One id per delivery, not one id for everything: two projects must not
    collapse into each other."""
    repository = _CollectingRepository()

    await _write_one_delivery(repository, uuid4(), uuid4())
    await _write_one_delivery(repository, uuid4(), uuid4())

    assert len({draft.correlation_id for draft in repository.drafts}) == 2


async def test_the_engine_run_stays_distinguishable_through_causation_id() -> None:
    """Acceptance criterion 3: per-run identity moved to causation_id rather
    than being dropped. It is the run id the RunSpec was started with, so a
    ledger row joins to the run directory on disk."""
    project_id = uuid4()
    run_id = uuid4()
    repository = _CollectingRepository()

    await _write_one_delivery(repository, project_id, run_id)

    by_phase = {draft.phase: draft for draft in repository.drafts}
    assert by_phase[Phase.BUILD].causation_id == run_id
    # Events vibey writes on its own account have no causing run.
    assert by_phase[Phase.DESIGN].causation_id is None
    assert by_phase[Phase.REVIEW].causation_id is None


async def test_a_deployment_can_partition_the_namespace() -> None:
    """ADR-0018: the namespace is a parameter every write site takes, so a
    deployment can keep its deliveries in a namespace of its own."""
    project_id = uuid4()
    namespace = UUID("00000000-0000-5000-8000-0000000000ff")
    repository = _CollectingRepository()
    correlation = DeliveryCorrelation(namespace)

    await PostgresReviewLedger(repository, correlation=correlation).append_event(  # type: ignore[arg-type]
        project_id,
        1,
        uuid4(),
        EventKind.VERDICT_RENDERED,
        {"complete": True},
    )

    assert repository.drafts[0].correlation_id == correlation.for_project(project_id).value
    assert (
        repository.drafts[0].correlation_id != DeliveryCorrelation().for_project(project_id).value
    )
