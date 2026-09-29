# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from tests.application.fakes import make_job
from vibey.application.design import DesignEvent
from vibey.application.design_synthesis_handler import (
    DesignSpecHandler,
    DesignSynthesizeHandler,
)
from vibey.application.research_gaps import RESEARCH_GAP_RECORDS
from vibey.application.worker import Failure, Success
from vibey.domain.job import FailureClass
from vibey.domain.research_gap import ResearchGap
from vibey.domain.spec import AcceptanceCriterion, DesignSpec


def spec() -> DesignSpec:
    return DesignSpec(
        "Ship the design",
        (),
        (),
        (AcceptanceCriterion("AC-1", "an idea", "accepted", "build starts", "guard allows"),),
        (),
        "one accepted criterion",
    )


class FakeLedger:
    async def append(self, *args):  # type: ignore[no-untyped-def]
        return None

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        return ()


class FakeSynthesizer:
    def __init__(self, result: DesignSpec) -> None:
        self.result = result

    async def synthesize(self, events):  # type: ignore[no-untyped-def]
        return self.result


class FakeSpecs:
    def __init__(self) -> None:
        self.value: DesignSpec | None = None
        self.published = False

    async def save(self, project_id: UUID, cycle: int, value: DesignSpec) -> None:
        self.value = value

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None:
        return self.value

    async def publish(self, project_id: UUID, cycle: int, value: DesignSpec) -> None:
        self.published = True


async def test_synthesize_saves_a_buildable_spec() -> None:
    job = replace(make_job(uuid4()), kind="design.synthesize")
    specs = FakeSpecs()
    outcome = await DesignSynthesizeHandler(
        ledger=FakeLedger(), synthesizer=FakeSynthesizer(spec()), specs=specs
    ).handle(job)
    assert isinstance(outcome, Success)
    assert specs.value == spec()


class GapLedger(FakeLedger):
    def __init__(self, events: tuple[DesignEvent, ...]) -> None:
        self.events = events

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        return self.events


async def test_synthesize_states_every_gap_the_ledger_recorded_whatever_the_model_wrote() -> None:
    """The gaps come from the ledger, not the synthesizer: a model that says nothing about
    an unresearched topic cannot make the spec silent about it."""
    now = datetime(2026, 9, 29, tzinfo=UTC)
    gap = ResearchGap("prior-art", "a local model has no web access.")
    ledger = GapLedger(
        (
            RESEARCH_GAP_RECORDS.event(gap, now=now, cycle=1),
            RESEARCH_GAP_RECORDS.event(ResearchGap("libraries", "cycle two"), now=now, cycle=2),
        )
    )
    specs = FakeSpecs()
    job = replace(make_job(uuid4()), kind="design.synthesize")
    assert job.cycle == 1

    outcome = await DesignSynthesizeHandler(
        ledger=ledger, synthesizer=FakeSynthesizer(spec()), specs=specs
    ).handle(job)

    assert outcome == Success({"acceptance_criteria": 1, "research_gaps": ["prior-art"]})
    assert specs.value == replace(spec(), research_gaps=(gap,))


async def test_synthesize_rejects_wrong_kind_and_unbuildable_result() -> None:
    specs = FakeSpecs()
    handler = DesignSynthesizeHandler(
        ledger=FakeLedger(),
        synthesizer=FakeSynthesizer(DesignSpec("", (), (), (), (), "")),
        specs=specs,
    )
    assert await handler.handle(make_job(uuid4())) == Failure(
        FailureClass.VIBEY, "expected design.synthesize job"
    )
    outcome = await handler.handle(replace(make_job(uuid4()), kind="design.synthesize"))
    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK


async def test_spec_handler_publishes_saved_buildable_spec() -> None:
    job = replace(make_job(uuid4()), kind="design.spec")
    specs = FakeSpecs()
    specs.value = spec()
    outcome = await DesignSpecHandler(specs=specs).handle(job)
    assert isinstance(outcome, Success)
    assert specs.published


async def test_spec_handler_rejects_wrong_kind_and_missing_spec() -> None:
    handler = DesignSpecHandler(specs=FakeSpecs())
    assert await handler.handle(make_job(uuid4())) == Failure(
        FailureClass.VIBEY, "expected design.spec job"
    )
    missing = await handler.handle(replace(make_job(uuid4()), kind="design.spec"))
    assert missing == Failure(FailureClass.WORK, "no synthesized design spec exists")
