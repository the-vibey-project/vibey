# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The interview declares each default under the project's `default_scope`.

The #998 failure end to end, at the application seam: the model asks "Should we add a
unit test ...?" and defaults "Yes"; an unattended caller answers `accept_defaults`. Under
the narrowest scope the recorded default -- and so the accepted answer -- is "No", and
the model's own "Yes" is kept in the QuestionAsked payload beside it.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from tests.application.test_design_handler import FakeDesignLedger, FixedClock
from vibey.application.design import (
    QUESTION_DEFAULT_CONTRACT,
    DesignEvent,
    DesignQuestion,
    DesignStage,
    QuestionBatch,
)
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.dto import JobRecord, ProjectRecord
from vibey.application.worker import Park
from vibey.domain.config import ConfigError
from vibey.domain.design_default_scope import NARROWEST_DEFAULT
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase

NOW = datetime(2026, 9, 29, tzinfo=UTC)
INTAKE = "docs(readme): add a table of contents to README.md"
WIDENING = "Should we add a unit test to verify the TOC is up-to-date"
HOW = "Should the anchor generation follow GitHub's algorithm exactly"


class WideningProvider:
    """The #998 shape: one scope-widening question, one how-question, both "Yes"."""

    async def batch(self, stage: DesignStage, prior_events: object) -> QuestionBatch:
        return QuestionBatch(
            stage,
            (
                DesignQuestion("q-test", WIDENING, "Yes", blocking=True),
                DesignQuestion("q-anchor", HOW, "Yes", blocking=False),
            ),
        )


class FakeProjects:
    def __init__(self, project_id: UUID, config: Mapping[str, object] | None) -> None:
        self._project_id = project_id
        self._record = (
            None
            if config is None
            else ProjectRecord(
                project_id=project_id,
                name="p",
                repo_path=Path("/repo"),
                phase=Phase.DESIGN,
                cycle=1,
                max_cycles=5,
                config=config,
                created_at=NOW,
                updated_at=NOW,
            )
        )

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._record if project_id == self._project_id else None

    async def transition(
        self, project_id: UUID, *, expected: Phase, to: Phase, guard: str | None = None
    ) -> ProjectRecord:
        raise NotImplementedError


def _seeded_ledger() -> FakeDesignLedger:
    ledger = FakeDesignLedger()
    ledger.events.append(
        DesignEvent(
            kind=EventKind.TRANSCRIPT_RECORDED,
            provenance=Provenance.UNTRUSTED,
            produced_at=NOW,
            payload={"text": INTAKE, "source": "github-issue"},
        )
    )
    return ledger


def _handler(
    ledger: FakeDesignLedger,
    gates: FakeHumanGateRepository,
    *,
    projects: FakeProjects | None = None,
) -> DesignInterviewHandler:
    return DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=WideningProvider(),
        clock=FixedClock(),
        interviewer=EngineId.GPTOSSLOOP,
        projects=projects,
    )


def _asked(ledger: FakeDesignLedger) -> dict[str, Mapping[str, object]]:
    return {
        str(event.payload["item_id"]): event.payload
        for event in ledger.events
        if event.kind is EventKind.QUESTION_ASKED
    }


def _answers(ledger: FakeDesignLedger) -> dict[str, object]:
    return {
        str(event.payload["item_id"]): event.payload["answer"]
        for event in ledger.events
        if event.kind is EventKind.ANSWER_GIVEN
    }


async def _accept_defaults(
    handler: DesignInterviewHandler, gates: FakeHumanGateRepository, job: JobRecord
) -> Park:
    first = await handler.handle(job)
    assert isinstance(first, Park)
    gate = await gates.raise_gate(job.project_id, job.id, first.request)
    await gates.answer(gate.gate_id, answer={"accept_defaults": True}, answered_by="bridge")
    await handler.handle(job)
    return first


async def test_accepting_defaults_takes_the_narrowed_default_and_keeps_the_models() -> None:
    job = make_job(uuid4())
    ledger, gates = _seeded_ledger(), FakeHumanGateRepository()

    first = await _accept_defaults(_handler(ledger, gates), gates, job)

    asked = _asked(ledger)
    assert asked["q-test"]["default"] == NARROWEST_DEFAULT
    assert asked["q-test"]["model_default"] == "Yes"
    assert "test" in str(asked["q-test"]["default_reason"])
    # The how-question is not scope-widening: its default stands and carries no rewrite.
    assert asked["q-anchor"]["default"] == "Yes"
    assert "model_default" not in asked["q-anchor"]
    assert _answers(ledger) == {"q-test": NARROWEST_DEFAULT, "q-anchor": "Yes"}
    # A person reading the gate sees both the narrowed default and what it replaced.
    assert f"[default: {NARROWEST_DEFAULT}; narrowed from the model's 'Yes']" in (
        first.request.prompt
    )


async def test_a_reparked_gate_is_rebuilt_from_the_ledger_with_the_narrowing() -> None:
    job = make_job(uuid4())
    ledger, gates = _seeded_ledger(), FakeHumanGateRepository()
    handler = _handler(ledger, gates)

    await handler.handle(job)
    again = await handler.handle(job)  # no answer yet: re-park from the recorded batch

    assert isinstance(again, Park)
    assert "narrowed from the model's 'Yes'" in again.request.prompt
    assert len(_asked(ledger)) == 2  # replay records nothing twice


async def test_a_project_that_declares_the_model_scope_keeps_the_models_default() -> None:
    job = make_job(uuid4())
    ledger, gates = _seeded_ledger(), FakeHumanGateRepository()
    projects = FakeProjects(job.project_id, {"design": {"interview": {"default_scope": "model"}}})

    await _accept_defaults(_handler(ledger, gates, projects=projects), gates, job)

    assert "model_default" not in _asked(ledger)["q-test"]
    assert _answers(ledger)["q-test"] == "Yes"


@pytest.mark.parametrize("config", [{}, None], ids=["nothing-declared", "no-project-row"])
async def test_an_undeclared_scope_is_narrowest(config: Mapping[str, object] | None) -> None:
    job = make_job(uuid4())
    ledger, gates = _seeded_ledger(), FakeHumanGateRepository()
    projects = FakeProjects(job.project_id, config)

    await _accept_defaults(_handler(ledger, gates, projects=projects), gates, job)

    assert _answers(ledger)["q-test"] == NARROWEST_DEFAULT


async def test_a_malformed_stored_scope_fails_the_job_rather_than_reading_as_narrowest() -> None:
    job = make_job(uuid4())
    ledger, gates = _seeded_ledger(), FakeHumanGateRepository()
    projects = FakeProjects(job.project_id, {"design": {"interview": {"default_scope": "wide"}}})

    with pytest.raises(ConfigError):
        await _handler(ledger, gates, projects=projects).handle(job)
    assert _asked(ledger) == {}


def test_the_contract_says_the_deliverable_itself_is_never_optional() -> None:
    """#963: the model itself defaulted "Should the lane commit the change to README.md?"
    to "No" (no `model_default` in the ledger -- the guard had not touched it). The
    contract both providers state now says narrowest is never less than the intake."""
    assert "The deliverable itself is never optional" in QUESTION_DEFAULT_CONTRACT
    assert "never less than it" in QUESTION_DEFAULT_CONTRACT
    assert "committing or applying the change the intake asks for" in QUESTION_DEFAULT_CONTRACT
