# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable ``design.interview`` handler for the seven-stage protocol."""

from collections.abc import Mapping, Sequence
from dataclasses import replace

from vibey.application.design import (
    DesignEvent,
    DesignQuestion,
    DesignStage,
    QuestionBatch,
    answer_questions,
    finalize_questions,
    stages_for_cycle,
)
from vibey.application.dto import EnqueueRequest, HumanGateRequest, JobRecord
from vibey.application.interfaces import (
    DesignLedger,
    DesignQuestionProvider,
)
from vibey.application.interfaces.projects import ProjectStore
from vibey.application.ports import Clock, HumanGateRepository, JobRepository
from vibey.application.worker import Outcome, Park, Success
from vibey.domain.config import DesignConfig
from vibey.domain.design_default_scope import DEFAULT_SCOPE, DESIGN_DEFAULT_SCOPE, DefaultScope
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.interfaces.design_default_scope_interface import (
    DesignDefaultScopeGuardInterface,
)
from vibey.domain.job import idempotency_key
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase


class DesignInterviewHandler:
    def __init__(
        self,
        *,
        ledger: DesignLedger,
        jobs: JobRepository,
        gates: HumanGateRepository,
        questions: DesignQuestionProvider,
        clock: Clock,
        interviewer: EngineId | None,
        projects: ProjectStore | None = None,
        scope_guard: DesignDefaultScopeGuardInterface = DESIGN_DEFAULT_SCOPE,
    ) -> None:
        """`projects` is where `[design.interview] default_scope` is read from, in the
        project's stored config; without it (or without the key) the declared default,
        narrowest, applies."""
        self._ledger = ledger
        self._jobs = jobs
        self._gates = gates
        self._questions = questions
        self._clock = clock
        self._interviewer = interviewer
        self._projects = projects
        self._scope_guard = scope_guard

    async def handle(self, job: JobRecord) -> Outcome:
        events = list(await self._ledger.all_for_project(job.project_id))
        stages = stages_for_cycle(job.cycle)
        for stage in stages:
            questions = _questions_for_stage(events, stage, cycle=job.cycle)
            if not questions:
                batch = await self._narrowed(
                    job, await self._questions.batch(stage, events), events
                )
                for event in batch.events(now=self._clock.now(), cycle=job.cycle):
                    await self._append(job, event)
                    events.append(event)
                return Park(_gate_for(batch))

            answered_ids = _answered_ids(events)
            if not all(question.question_id in answered_ids for question in questions):
                gate = await self._gates.latest_for_job(job.id)
                if gate is None or gate.answer is None or stage.value not in gate.prompt:
                    return Park(_gate_for(QuestionBatch(stage, questions)))
                answers = _answers_from(gate.answer)
                if bool(gate.answer.get("accept_defaults")):
                    # The designed zero-touch path: every question not
                    # explicitly answered takes its default, blocking ones
                    # included. Question KEYS are model-minted and vary
                    # per run, so an unattended caller cannot know them --
                    # this contract needs none.
                    answers = {
                        question.question_id: question.default for question in questions
                    } | answers
                for event in answer_questions(questions, answers, now=self._clock.now()):
                    if str(event.payload["item_id"]) not in answered_ids:
                        await self._append(job, event)
                        events.append(event)
                answered_ids = _answered_ids(events)
                try:
                    defaults = finalize_questions(
                        questions, answered_ids=answered_ids, now=self._clock.now()
                    )
                except ValueError:
                    return Park(_gate_for(QuestionBatch(stage, questions)))
                for event in defaults:
                    if str(event.payload["item_id"]) not in _assumed_ids(events):
                        await self._append(job, event)
                        events.append(event)

        await self._enqueue_followups(job)
        return Success({"stages": len(stages)})

    async def _narrowed(
        self, job: JobRecord, batch: QuestionBatch, events: Sequence[DesignEvent]
    ) -> QuestionBatch:
        """The batch with each default declared under the project's `default_scope`.

        Applied before the questions are recorded, so the default a person sees in the
        gate, the one `accept_defaults` takes and the assumption an unanswered question
        becomes are all the same narrowed value -- and the model's own stays in the
        QuestionAsked payload beside it. The intake is whatever issue text seeded the
        ledger; the guard only reads it for which artefacts it names.
        """
        policy = await self._policy(job)
        intake = "\n".join(
            str(event.payload.get("text", ""))
            for event in events
            if event.kind is EventKind.TRANSCRIPT_RECORDED
        )
        narrowed = []
        for question in batch.questions:
            scoped = self._scope_guard.scope(
                question.text, question.default, intake=intake, policy=policy
            )
            narrowed.append(
                replace(
                    question,
                    default=scoped.default,
                    model_default=scoped.model_default,
                    default_reason=scoped.reason,
                )
                if scoped.rewritten
                else question
            )
        return QuestionBatch(batch.stage, tuple(narrowed))

    async def _policy(self, job: JobRecord) -> DefaultScope:
        if self._projects is None:
            return DEFAULT_SCOPE
        project = await self._projects.get(job.project_id)
        if project is None:
            return DEFAULT_SCOPE
        # A malformed stored value raises: a declaration that cannot be read is not the
        # same fact as no declaration, and must not quietly read as narrowest (10.f).
        return DesignConfig.from_data(project.config).interview.default_scope

    async def _append(self, job: JobRecord, event: DesignEvent) -> None:
        await self._ledger.append(job.project_id, job.cycle, job.id, self._interviewer, event)

    async def _enqueue_followups(self, job: JobRecord) -> None:
        research_jobs = []
        for topic in ("prior-art", "libraries", "api-docs"):
            research_jobs.append(
                await self._jobs.enqueue(
                    EnqueueRequest(
                        project_id=job.project_id,
                        cycle=job.cycle,
                        phase=Phase.DESIGN,
                        kind="design.research",
                        idempotency_key=idempotency_key(
                            job.project_id, job.cycle, "design.research", topic
                        ),
                        payload={"topic": topic},
                        requirement={"effort": Effort.STANDARD.name.lower()},
                    )
                )
            )
        synth = await self._jobs.enqueue(
            EnqueueRequest(
                project_id=job.project_id,
                cycle=job.cycle,
                phase=Phase.DESIGN,
                kind="design.synthesize",
                idempotency_key=idempotency_key(
                    job.project_id, job.cycle, "design.synthesize", "spec"
                ),
                # The "a different engine synthesises than interviewed"
                # constraint is derived from whoever actually interviewed, never
                # from a literal: on the sovereign path that is gptossloop, and on
                # the scripted path no engine interviewed at all, so nothing is
                # excluded.
                requirement={
                    "effort": Effort.HIGH.name.lower(),
                    "excluded": [] if self._interviewer is None else [self._interviewer.value],
                },
                depends_on=tuple(item.id for item in research_jobs),
            )
        )
        await self._jobs.enqueue(
            EnqueueRequest(
                project_id=job.project_id,
                cycle=job.cycle,
                phase=Phase.DESIGN,
                kind="design.spec",
                idempotency_key=idempotency_key(job.project_id, job.cycle, "design.spec", "final"),
                requirement={"effort": Effort.HIGH.name.lower()},
                depends_on=(synth.id,),
            )
        )


def _questions_for_stage(
    events: Sequence[DesignEvent], stage: DesignStage, *, cycle: int | None = None
) -> tuple[DesignQuestion, ...]:
    return tuple(
        DesignQuestion(
            question_id=str(event.payload["item_id"]),
            text=str(event.payload["text"]),
            default=str(event.payload["default"]),
            blocking=bool(event.payload["blocking"]),
            model_default=_optional_text(event.payload.get("model_default")),
            default_reason=_optional_text(event.payload.get("default_reason")),
        )
        for event in events
        if event.kind is EventKind.QUESTION_ASKED
        and event.payload.get("stage") == stage.value
        and (cycle is None or event.payload.get("cycle", cycle) == cycle)
    )


def _optional_text(value: object) -> str | None:
    return None if value is None else str(value)


def _answered_ids(events: Sequence[DesignEvent]) -> frozenset[str]:
    return frozenset(
        str(event.payload["item_id"]) for event in events if event.kind is EventKind.ANSWER_GIVEN
    )


def _assumed_ids(events: Sequence[DesignEvent]) -> frozenset[str]:
    return frozenset(
        str(event.payload["item_id"])
        for event in events
        if event.kind is EventKind.ASSUMPTION_STATED
    )


def _answers_from(answer: Mapping[str, object]) -> dict[str, str]:
    raw = answer.get("answers")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _gate_for(batch: QuestionBatch) -> HumanGateRequest:
    prompt = f"{batch.stage.value}: " + " | ".join(
        f"{question.question_id}: {question.text} [default: {question.default}"
        + (
            ""
            if question.model_default is None
            else f"; narrowed from the model's {question.model_default!r}"
        )
        + "]"
        for question in batch.questions
    )
    return HumanGateRequest(
        kind="question",
        prompt=prompt,
        options=tuple(question.default for question in batch.questions),
    )


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "DesignLedger",
    "DesignQuestionProvider",
]
