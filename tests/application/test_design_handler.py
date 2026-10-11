# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.design import DESIGN_STAGES, DesignEvent, DesignQuestion, QuestionBatch
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.worker import Park, Success
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 14, tzinfo=UTC)


class FakeDesignLedger:
    def __init__(self) -> None:
        self.events: list[DesignEvent] = []
        self.engines: list[EngineId | None] = []

    async def append(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        engine_id: EngineId | None,
        event: DesignEvent,
    ) -> None:
        self.events.append(event)
        self.engines.append(engine_id)

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        return tuple(self.events)


class ScriptedQuestionProvider:
    async def batch(self, stage, prior_events):  # type: ignore[no-untyped-def]
        number = DESIGN_STAGES.index(stage) + 1
        return QuestionBatch(
            stage,
            (
                DesignQuestion(
                    f"q-{number}",
                    f"Stage {number}?",
                    f"default-{number}",
                    blocking=number == 1,
                ),
            ),
        )


async def test_scripted_user_completes_all_seven_stages_and_enqueues_design_jobs() -> None:
    project_id = uuid4()
    job = make_job(project_id)
    job = job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.DESIGN,
        kind="design.interview",
    )
    jobs = FakeJobRepository()
    gates = FakeHumanGateRepository()
    ledger = FakeDesignLedger()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=jobs,
        gates=gates,
        questions=ScriptedQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CLAUDELOOP,
    )

    for index, stage in enumerate(DESIGN_STAGES):
        outcome = await handler.handle(job)
        assert isinstance(outcome, Park)
        assert stage.value in outcome.request.prompt
        raised = await gates.raise_gate(project_id, job.id, outcome.request)
        answer = {"answers": {f"q-{index + 1}": f"answer-{index + 1}"}}
        await gates.answer(raised.gate_id, answer=answer, answered_by="scripted-user")

    outcome = await handler.handle(job)
    assert isinstance(outcome, Success)
    kinds = [event.kind for event in ledger.events]
    assert kinds.count(EventKind.QUESTION_ASKED) == 7
    assert kinds.count(EventKind.ANSWER_GIVEN) == 7

    enqueued = list(jobs._jobs.values())
    assert [record.kind for record in enqueued].count("design.research") == 3
    synth = next(record for record in enqueued if record.kind == "design.synthesize")
    spec = next(record for record in enqueued if record.kind == "design.spec")
    assert synth.requirement["excluded"] == [EngineId.CLAUDELOOP.value]
    assert spec.phase is Phase.DESIGN


async def test_replay_does_not_duplicate_an_open_question_batch() -> None:
    project_id = uuid4()
    job = make_job(project_id)
    ledger = FakeDesignLedger()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=FakeHumanGateRepository(),
        questions=ScriptedQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CODEXLOOP,
    )
    first = await handler.handle(job)
    second = await handler.handle(job)
    assert isinstance(first, Park)
    assert isinstance(second, Park)
    assert len(ledger.events) == 1


async def test_nonblocking_default_is_recorded_when_batch_answer_omits_it() -> None:
    project_id = uuid4()
    job = make_job(project_id)
    ledger = FakeDesignLedger()
    gates = FakeHumanGateRepository()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=ScriptedQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CODEXLOOP,
    )
    first = await handler.handle(job)
    assert isinstance(first, Park)
    gate = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(gate.gate_id, answer={"answers": {"q-1": "yes"}}, answered_by="user")
    second = await handler.handle(job)
    assert isinstance(second, Park)
    gate = await gates.raise_gate(project_id, job.id, second.request)
    await gates.answer(gate.gate_id, answer={"answers": {}}, answered_by="user")
    await handler.handle(job)
    assumption = next(event for event in ledger.events if event.kind is EventKind.ASSUMPTION_STATED)
    assert assumption.payload["text"] == "default-2"


async def test_blocking_question_reparks_when_answer_payload_is_missing() -> None:
    project_id = uuid4()
    job = make_job(project_id)
    ledger = FakeDesignLedger()
    gates = FakeHumanGateRepository()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=ScriptedQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.QWENLOOP,
    )
    first = await handler.handle(job)
    assert isinstance(first, Park)
    gate = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(gate.gate_id, answer={"text": "not structured"}, answered_by="user")
    replay = await handler.handle(job)
    assert isinstance(replay, Park)
    assert "q-1" in replay.request.prompt


class TwoQuestionProvider:
    async def batch(self, stage, prior_events):  # type: ignore[no-untyped-def]
        return QuestionBatch(
            stage,
            (
                DesignQuestion("q-a", "Question A?", "def-a", blocking=True),
                DesignQuestion("q-b", "Question B?", "def-b", blocking=False),
            ),
        )


async def test_replay_skips_already_answered_and_already_assumed_items() -> None:
    """On idempotent replay, answer events for items already recorded
    are skipped (65->64), and assumption events for items already assumed
    are skipped (76->75)."""
    project_id = uuid4()
    job = make_job(project_id)
    job = job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.DESIGN,
        kind="design.interview",
    )
    ledger = FakeDesignLedger()
    gates = FakeHumanGateRepository()
    now = FixedClock().now()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=TwoQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CLAUDELOOP,
    )

    # Step 1: handler asks both questions -> Park
    outcome1 = await handler.handle(job)
    assert isinstance(outcome1, Park)

    # Step 2: answer the gate with only q-a
    gate = await gates.raise_gate(project_id, job.id, outcome1.request)
    await gates.answer(gate.gate_id, answer={"answers": {"q-a": "yes"}}, answered_by="user")

    # Step 3: pre-seed ledger with ANSWER_GIVEN for q-a and ASSUMPTION_STATED for q-b
    # simulating a prior handler run that already committed these events
    ledger.events.append(
        DesignEvent(
            kind=EventKind.ANSWER_GIVEN,
            provenance=Provenance.TRUSTED,
            produced_at=now,
            payload={"item_id": "q-a", "answer": "yes"},
        )
    )
    ledger.events.append(
        DesignEvent(
            kind=EventKind.ASSUMPTION_STATED,
            provenance=Provenance.TRUSTED,
            produced_at=now,
            payload={"item_id": "q-b", "text": "def-b", "question": "Question B?"},
        )
    )

    # Step 4: replay — handler should skip already-answered q-a and already-assumed q-b
    outcome2 = await handler.handle(job)
    # Should proceed past stage 1 to stage 2 and Park with new questions
    assert isinstance(outcome2, Park)

    # Verify no duplicate answer/assumption events were appended
    answer_events = [
        e
        for e in ledger.events
        if e.kind is EventKind.ANSWER_GIVEN and e.payload["item_id"] == "q-a"
    ]
    assumption_events = [
        e
        for e in ledger.events
        if e.kind is EventKind.ASSUMPTION_STATED and e.payload["item_id"] == "q-b"
    ]
    assert len(answer_events) == 1
    assert len(assumption_events) == 1


async def test_accept_defaults_answers_everything_including_blocking_questions() -> None:
    """The zero-touch contract: question KEYS are model-minted and vary
    per run, so an unattended caller cannot know them -- accept_defaults
    takes every default, blocking included, with no keys at all."""
    project_id = uuid4()
    job = make_job(project_id)
    ledger = FakeDesignLedger()
    gates = FakeHumanGateRepository()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=TwoQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CLAUDELOOP,
    )
    first = await handler.handle(job)
    assert isinstance(first, Park)
    gate = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(gate.gate_id, answer={"accept_defaults": True}, answered_by="driver")

    outcome = await handler.handle(job)

    # The stage advanced past both questions (blocking q-a included).
    answered = [
        event.payload["item_id"] for event in ledger.events if event.kind is EventKind.ANSWER_GIVEN
    ]
    assert "q-a" in answered and "q-b" in answered
    answers = {
        event.payload["item_id"]: event.payload["answer"]
        for event in ledger.events
        if event.kind is EventKind.ANSWER_GIVEN
    }
    assert answers["q-a"] == "def-a"
    assert answers["q-b"] == "def-b"
    # The handler advanced past the first stage: the next park (the
    # provider reuses question ids) is for the FOLLOWING stage.
    assert isinstance(outcome, Park)
    assert not outcome.request.prompt.startswith("context_free")


async def test_accept_defaults_keeps_explicit_answers_over_defaults() -> None:
    project_id = uuid4()
    job = make_job(project_id)
    ledger = FakeDesignLedger()
    gates = FakeHumanGateRepository()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=TwoQuestionProvider(),
        clock=FixedClock(),
        interviewer=EngineId.CLAUDELOOP,
    )
    first = await handler.handle(job)
    assert isinstance(first, Park)
    gate = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(
        gate.gate_id,
        answer={"accept_defaults": True, "answers": {"q-a": "explicit answer"}},
        answered_by="driver",
    )

    await handler.handle(job)

    answers = {
        event.payload["item_id"]: event.payload["answer"]
        for event in ledger.events
        if event.kind is EventKind.ANSWER_GIVEN
    }
    assert answers["q-a"] == "explicit answer"
    assert answers["q-b"] == "def-b"


async def test_an_interview_no_engine_ran_names_none_and_excludes_none() -> None:
    """The scripted path has no engine, so it claims none and bars none.

    `excluded` on design.synthesize exists to keep synthesis off the engine that
    interviewed. With no interviewer there is nobody to keep off, and inventing
    one would put a false actor in an append-only record.
    """
    project_id = uuid4()
    job = make_job(project_id)
    job = job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.DESIGN,
        kind="design.interview",
    )
    jobs = FakeJobRepository()
    gates = FakeHumanGateRepository()
    ledger = FakeDesignLedger()
    handler = DesignInterviewHandler(
        ledger=ledger,
        jobs=jobs,
        gates=gates,
        questions=ScriptedQuestionProvider(),
        clock=FixedClock(),
        interviewer=None,
    )

    for index, _stage in enumerate(DESIGN_STAGES):
        outcome = await handler.handle(job)
        assert isinstance(outcome, Park)
        raised = await gates.raise_gate(project_id, job.id, outcome.request)
        await gates.answer(
            raised.gate_id,
            answer={"answers": {f"q-{index + 1}": f"answer-{index + 1}"}},
            answered_by="scripted-user",
        )

    assert isinstance(await handler.handle(job), Success)
    assert set(ledger.engines) == {None}
    synth = next(record for record in jobs._jobs.values() if record.kind == "design.synthesize")
    assert synth.requirement["excluded"] == []


# ── a stage with nothing left to ask is settled, not asked again ─────────────


class QuietQuestionProvider:
    """Asks one question at the first stage and has nothing to ask at any other."""

    def __init__(self) -> None:
        self.calls: list[object] = []

    async def batch(self, stage, prior_events):  # type: ignore[no-untyped-def]
        self.calls.append(stage)
        if stage is DESIGN_STAGES[0]:
            return QuestionBatch(
                stage, (DesignQuestion("q-1", "Stage 1?", "default-1", blocking=False),)
            )
        return QuestionBatch(stage, ())


def _design_job(project_id: UUID):  # type: ignore[no-untyped-def]
    return replace(make_job(project_id), phase=Phase.DESIGN, kind="design.interview")


def _quiet_handler(provider: object, ledger: FakeDesignLedger, gates: FakeHumanGateRepository):  # type: ignore[no-untyped-def]
    return DesignInterviewHandler(
        ledger=ledger,
        jobs=FakeJobRepository(),
        gates=gates,
        questions=provider,  # type: ignore[arg-type]
        clock=FixedClock(),
        interviewer=EngineId.CLAUDELOOP,
    )


async def test_a_stage_with_nothing_to_ask_is_recorded_as_settled_with_no_gate() -> None:
    project_id = uuid4()
    job = _design_job(project_id)
    provider = QuietQuestionProvider()
    ledger, gates = FakeDesignLedger(), FakeHumanGateRepository()
    handler = _quiet_handler(provider, ledger, gates)

    first = await handler.handle(job)
    assert isinstance(first, Park)  # stage 1 really has a question
    raised = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(raised.gate_id, answer={"answers": {"q-1": "yes"}}, answered_by="user")

    second = await handler.handle(job)

    assert isinstance(second, Success)  # the six quiet stages never raised a gate
    kinds = [event.kind for event in ledger.events]
    assert kinds.count(EventKind.QUESTION_ASKED) == 1
    assert kinds.count(EventKind.STAGE_SETTLED) == len(DESIGN_STAGES) - 1
    settled = [e for e in ledger.events if e.kind is EventKind.STAGE_SETTLED]
    assert {e.payload["stage"] for e in settled} == {s.value for s in DESIGN_STAGES[1:]}
    assert all(e.payload["cycle"] == job.cycle for e in settled)
    assert all(e.provenance is Provenance.AGENT for e in settled)


async def test_a_settled_stage_is_not_asked_about_again_on_replay() -> None:
    project_id = uuid4()
    job = _design_job(project_id)
    provider = QuietQuestionProvider()
    ledger, gates = FakeDesignLedger(), FakeHumanGateRepository()
    handler = _quiet_handler(provider, ledger, gates)
    first = await handler.handle(job)
    assert isinstance(first, Park)
    raised = await gates.raise_gate(project_id, job.id, first.request)
    await gates.answer(raised.gate_id, answer={"answers": {"q-1": "yes"}}, answered_by="user")
    await handler.handle(job)
    asked = len(provider.calls)

    again = await handler.handle(job)

    assert isinstance(again, Success)
    assert len(provider.calls) == asked  # without the record, every replay asked them all again
    assert asked == len(DESIGN_STAGES)  # once per stage, ever


async def test_an_interview_with_nothing_to_ask_anywhere_finishes_without_a_gate() -> None:
    class Silent:
        async def batch(self, stage, prior_events):  # type: ignore[no-untyped-def]
            return QuestionBatch(stage, ())

    job = _design_job(uuid4())
    ledger = FakeDesignLedger()
    handler = _quiet_handler(Silent(), ledger, FakeHumanGateRepository())

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert [e.kind for e in ledger.events] == [EventKind.STAGE_SETTLED] * len(DESIGN_STAGES)
