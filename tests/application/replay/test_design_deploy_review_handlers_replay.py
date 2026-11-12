# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Replay cases for the design, deploy, review and visual handlers (SP2-A Task 8).

The same contract as ``test_build_handlers_replay.py``: the job sits READY in the fake queue,
the harness leases it, delivers it, lets the lease lapse and delivers the refreshed row
(attempt 2) to a NEW handler instance over the SAME persisted fakes, and the content of what
the handler left behind must not change.

What is compared, per case: the job rows (fan-out), the ledger entries, the gate rows (a
handler that parks must not raise a second gate on its redelivery), and whatever the
handler persists (specs, consents, inventories, review artifacts, the project's phase).

Two known allowances, both stated where they are made:

- The ledger is append-only and does not dedupe on identity (#1887), so a redelivery may
  restate an entry the first delivery wrote (``EntryBatches``); anything new or different
  still fails.
- A stored value is overwritten by a redelivery (a spec file, a consent file), so the fakes
  keep the last write, exactly as the real stores do.

The project's phase transition is the compare-and-set the real repository performs: a
second ``transition(expected=X, ...)`` after the first one moved the phase raises
``ValueError`` (``ProjectRepository.transition_on``). Every handler that makes a transition
is therefore run twice: with a transition that tolerates a replay, which isolates everything
else the handler does on a redelivery (``CASES``), and with that faithful compare-and-set,
where a redelivery raises (finding F-8-1, ``KNOWN_FINDINGS``).
"""

import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from tests.application.replay.harness import (
    EntryBatches,
    ReplayCase,
    ReplayRig,
    assert_replay_is_idempotent,
    jobs_content,
)
from tests.application.test_deploy_design_and_acceptance import _valid_spec
from tests.application.test_deploy_execute_handler import FakeAzureClient
from tests.application.test_deploy_execute_handler import _sample_spec as _execute_spec
from tests.application.test_design_research_handler import FixedResearcher, RefusingResearcher
from tests.application.test_design_synthesis_handler import FakeSpecs, FakeSynthesizer
from tests.application.test_design_synthesis_handler import spec as _synthesized_spec
from tests.application.test_review_demo_handler import (
    FakeReviewArtifactWriter,
    FakeSpecRepository,
    _FixedReviewer,
    _notes_spec,
)
from tests.application.test_review_deployment_choice import FakeProjectRepo
from tests.application.test_review_publish_handler import _Publisher, _spec, _Specs
from tests.application.test_visual_handler import FakeInventories, FakeProducer, inventory
from vibey.application.deploy_acceptance_handler import DeployAcceptanceHandler
from vibey.application.deploy_design_handler import DeployInterviewHandler, DeploySynthesizeHandler
from vibey.application.deploy_execute_handler import DeployExecuteHandler, DeployStep
from vibey.application.deploy_review_handler import (
    DeployReviewDemoHandler,
    DeployReviewTriageHandler,
)
from vibey.application.design import DesignEvent
from vibey.application.design_research_handler import DesignResearchHandler
from vibey.application.design_synthesis_handler import DesignSpecHandler, DesignSynthesizeHandler
from vibey.application.dto import JobRecord, ProjectRecord
from vibey.application.interfaces import AutomatedFinding
from vibey.application.research_gaps import RESEARCH_GAP_RECORDS
from vibey.application.review_collect_handler import ReviewCollectHandler
from vibey.application.review_demo_handler import ReviewDemoHandler
from vibey.application.review_deployment_choice_handler import ReviewDeploymentChoiceHandler
from vibey.application.review_publish_handler import ReviewPublishHandler
from vibey.application.review_triage_handler import ReviewTriageHandler
from vibey.application.visual_handler import VisualInventoryHandler, VisualPlanHandler
from vibey.application.worker import Park
from vibey.domain.deployment import DeploymentConsent
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.research_gap import ResearchGap, ResearchOnUnavailable
from vibey.domain.review import Severity

NOW = datetime(2026, 11, 11, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return NOW


# --------------------------------------------------------------------------------- fakes


class PhaseEntries(EntryBatches):
    """A ``PhaseLedger`` that keeps the content of every append, split by delivery."""

    def __init__(self, phase: Phase, seeded: Sequence[LedgerEvent] = ()) -> None:
        super().__init__()
        self._phase = phase
        self._events: list[LedgerEvent] = list(seeded)

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    async def append_event(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        kind: EventKind,
        payload: dict[str, object],
    ) -> None:
        self.add(
            {
                "project_id": project_id,
                "cycle": cycle,
                "job_id": job_id,
                "kind": kind,
                "payload": dict(payload),
            }
        )
        self._events.append(
            self.event(self._phase, kind, payload, project_id, cycle, seq=len(self._events) + 1)
        )

    @staticmethod
    def event(
        phase: Phase,
        kind: EventKind,
        payload: dict[str, object],
        project_id: UUID,
        cycle: int = 1,
        seq: int = 1,
    ) -> LedgerEvent:
        return LedgerEvent(
            event_id=uuid4(),
            project_id=project_id,
            cycle=cycle,
            phase=phase,
            seq=seq,
            kind=kind,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=uuid4(),
            provenance=Provenance.TRUSTED,
            produced_at=NOW,
            payload=dict(payload),
            digest=digest_event(payload),
        )


class DesignEntries(EntryBatches):
    """A ``DesignLedger`` that keeps the content of every append, split by delivery."""

    def __init__(self, seeded: Sequence[DesignEvent] = ()) -> None:
        super().__init__()
        self._events: list[DesignEvent] = list(seeded)

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        return tuple(self._events)

    async def append(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        engine_id: EngineId | None,
        event: DesignEvent,
    ) -> None:
        self.add(
            {
                "project_id": project_id,
                "cycle": cycle,
                "job_id": job_id,
                "engine_id": engine_id,
                "event": dataclasses.asdict(event),
            }
        )
        self._events.append(event)


class LastWrite:
    """A store that holds the last value written, as the real stores (a file each) do."""

    def __init__(self) -> None:
        self.value: object = None

    async def save_spec(self, project_id: UUID, spec: object) -> None:
        self.value = spec

    async def save_consent(self, project_id: UUID, consent: object) -> None:
        self.value = consent


class SpecBook(FakeSpecRepository):
    """Specs by cycle, last write wins (``save`` overwrites the cycle's file)."""

    def __init__(self, spec: object) -> None:
        super().__init__(spec)  # type: ignore[arg-type]
        self.saved: dict[int, object] = {}

    async def save(self, project_id: UUID, cycle: int, spec: object) -> None:
        self.saved[cycle] = spec


class CasProjects(FakeProjectRepo):
    """The project row, with the compare-and-set the real repository performs.

    ``replay_is_noop`` is the tolerant variant: a ``transition`` whose target is already the
    project's phase does nothing instead of raising, which isolates what the rest of a
    handler does on a redelivery from finding F-8-1."""

    def __init__(self, project_id: UUID, phase: Phase, *, replay_is_noop: bool) -> None:
        super().__init__(
            ProjectRecord(
                project_id=project_id,
                name="Demo Project",
                repo_path=Path("/work/demo"),
                phase=phase,
                cycle=1,
                max_cycles=3,
                config={},
                created_at=NOW,
                updated_at=NOW,
            )
        )
        self._noop = replay_is_noop

    async def transition(  # type: ignore[no-untyped-def,override]
        self, project_id, *, expected, to, cycle=None, guard=None
    ):
        if self.project.phase is not expected:
            if self._noop and self.project.phase is to:
                return self.project
            raise ValueError(f"project {project_id} is not in expected phase {expected.value!r}")
        return await super().transition(project_id, expected=expected, to=to, cycle=cycle)

    def standing(self) -> dict[str, object]:
        return {"phase": self.project.phase, "cycle": self.project.cycle}


def _job(kind: str, phase: Phase, project_id: UUID | None = None, **fields: Any) -> JobRecord:
    return replace(make_job(project_id or uuid4()), kind=kind, phase=phase, **fields)


def _gates_content(gates: FakeHumanGateRepository) -> list[dict[str, object]]:
    return [dataclasses.asdict(record) for record in gates.raised]


async def _park_then_answer(
    handler: Any, gates: FakeHumanGateRepository, job: JobRecord, answer: dict[str, object]
) -> None:
    """A person answering the gate the handler raised: the setup of a case that replays the
    delivery AFTER the answer (not part of what is replayed)."""
    parked = await handler.handle(job)
    assert isinstance(parked, Park)
    raised = gates.raised[-1]
    await gates.answer(raised.gate_id, answer=answer, answered_by="adam")


# ---------------------------------------------------------------------- deploy_acceptance


def _deploy_acceptance(*, answered: bool, replay_is_noop: bool) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("deploy.spec", Phase.DEPLOY_DESIGN, project_id)
        jobs = FakeJobRepository([job])
        gates = FakeHumanGateRepository()
        ledger = PhaseEntries(Phase.DEPLOY_DESIGN)
        consents = LastWrite()
        projects = CasProjects(project_id, Phase.DEPLOY_DESIGN, replay_is_noop=replay_is_noop)
        spec = _valid_spec()

        def handler() -> DeployAcceptanceHandler:
            return DeployAcceptanceHandler(
                ledger=ledger,
                gates=gates,
                jobs=jobs,
                projects=projects,
                clock=_Clock(),
                spec_provider=lambda _pid: spec,
                consent_store=consents,  # type: ignore[arg-type]
            )

        async def accept() -> None:
            await _park_then_answer(
                handler(),
                gates,
                job,
                {"verdict": "accept", "explicit_mutation_authorized": True},
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            prepare=accept if answered else None,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "gates": _gates_content(gates),
                "consent": consents.value,
                "project": projects.standing(),
            },
        )

    return build


# ----------------------------------------------------------------------- deploy_design


def _deploy_interview(scratch: Path) -> ReplayRig:
    """The interview answered: the delivery under replay records it and enqueues synthesis."""
    project_id = uuid4()
    job = _job("deploy.interview", Phase.DEPLOY_DESIGN, project_id)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    ledger = PhaseEntries(Phase.DEPLOY_DESIGN)

    def handler() -> DeployInterviewHandler:
        return DeployInterviewHandler(ledger=ledger, gates=gates, clock=_Clock(), jobs=jobs)

    async def answer() -> None:
        await _park_then_answer(handler(), gates, job, {"environment": "prod"})

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        prepare=answer,
        snapshot=lambda: {
            "ledger": ledger.after_delivery(),
            "jobs": jobs_content(jobs, job.id),
            "gates": _gates_content(gates),
        },
    )


def _deploy_synthesize(scratch: Path) -> ReplayRig:
    project_id = uuid4()
    job = _job("deploy.synthesize", Phase.DEPLOY_DESIGN, project_id)
    jobs = FakeJobRepository([job])
    answers = PhaseEntries.event(
        Phase.DEPLOY_DESIGN,
        EventKind.ANSWER_GIVEN,
        {"stage": "deploy_elicitation", "answer": {"environment": "prod", "region": "westeurope"}},
        project_id,
    )
    ledger = PhaseEntries(Phase.DEPLOY_DESIGN, seeded=[answers])
    specs = LastWrite()

    def handler() -> DeploySynthesizeHandler:
        return DeploySynthesizeHandler(
            ledger=ledger,
            clock=_Clock(),
            jobs=jobs,
            spec_store=specs,  # type: ignore[arg-type]
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": ledger.after_delivery(),
            "jobs": jobs_content(jobs, job.id),
            "spec": specs.value,
        },
    )


# ---------------------------------------------------------------------- deploy_execute


def _deploy_execute(*, fails: bool, replay_is_noop: bool) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("deploy.execute", Phase.DEPLOY_EXECUTE, project_id)
        jobs = FakeJobRepository([job])
        ledger = PhaseEntries(Phase.DEPLOY_EXECUTE)
        projects = CasProjects(project_id, Phase.DEPLOY_EXECUTE, replay_is_noop=replay_is_noop)
        azure = FakeAzureClient(fail_at_step=DeployStep.APPLY if fails else None)
        spec = _execute_spec()
        consent = DeploymentConsent("c-1", spec.scope_digest(), "user", NOW, True)

        def handler() -> DeployExecuteHandler:
            return DeployExecuteHandler(
                ledger=ledger,
                jobs=jobs,
                projects=projects,
                azure_client=azure,
                clock=_Clock(),
                spec_provider=lambda _pid: spec,
                consent_provider=lambda _pid: consent,
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "project": projects.standing(),
                # Which graph steps ran, not how often: the apply is keyed by the spec id
                # (`dep-<spec_id>`), so applying the same spec again lands on the same
                # deployment. The fake azure client logs calls, it does not model that.
                "azure_steps": sorted({step.value for step in azure.steps_run}),
            },
        )

    return build


# ----------------------------------------------------------------------- deploy_review


def _deploy_review(
    kind: str, answer: dict[str, object] | None, *, seeded: bool = False
) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job(kind, Phase.DEPLOY_REVIEW, project_id)
        jobs = FakeJobRepository([job])
        gates = FakeHumanGateRepository()
        events = []
        if seeded and kind == "deploy.demo":
            events.append(
                PhaseEntries.event(
                    Phase.DEPLOY_EXECUTE,
                    EventKind.ARTIFACT_PRODUCED,
                    {
                        "artifact_type": "deployment_verification",
                        "outputs": {"endpoint": "https://live.example.test"},
                    },
                    project_id,
                )
            )
        if seeded and kind == "deploy.triage":
            events.append(
                PhaseEntries.event(
                    Phase.DEPLOY_EXECUTE,
                    EventKind.FINDING_RAISED,
                    {"failure_class": "policy_denial", "error": "denied by policy"},
                    project_id,
                )
            )
        ledger = PhaseEntries(Phase.DEPLOY_REVIEW, seeded=events)
        handler_type = (
            DeployReviewDemoHandler if kind == "deploy.demo" else DeployReviewTriageHandler
        )

        def handler() -> Any:
            return handler_type(ledger=ledger, human_gates=gates, jobs=jobs)

        async def answered() -> None:
            assert answer is not None
            await _park_then_answer(handler(), gates, job, answer)

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            prepare=answered if answer is not None else None,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "gates": _gates_content(gates),
            },
        )

    return build


# --------------------------------------------------------------------- design_research


def _design_research(*, gap: bool) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        job = _job("design.research", Phase.DESIGN, payload={"topic": "prior-art"})
        jobs = FakeJobRepository([job])
        ledger = DesignEntries()
        researcher: Any = RefusingResearcher("prior-art.md") if gap else FixedResearcher()

        def handler() -> DesignResearchHandler:
            return DesignResearchHandler(
                ledger=ledger,
                researcher=researcher,
                clock=_Clock(),
                engine_id=EngineId.CODEXLOOP,
                on_unavailable=ResearchOnUnavailable.RECORD_GAP
                if gap
                else ResearchOnUnavailable.GATE,
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
            },
        )

    return build


# ------------------------------------------------------------------- design_synthesis


def _design_synthesize(scratch: Path) -> ReplayRig:
    job = _job("design.synthesize", Phase.DESIGN)
    jobs = FakeJobRepository([job])
    gap = RESEARCH_GAP_RECORDS.event(ResearchGap("prior-art", "no web"), now=NOW, cycle=1)
    ledger = DesignEntries(seeded=[gap])
    specs = FakeSpecs()

    def handler() -> DesignSynthesizeHandler:
        return DesignSynthesizeHandler(
            ledger=ledger, synthesizer=FakeSynthesizer(_synthesized_spec()), specs=specs
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": ledger.after_delivery(),
            "jobs": jobs_content(jobs, job.id),
            "spec": specs.value,
        },
    )


def _design_spec(scratch: Path) -> ReplayRig:
    job = _job("design.spec", Phase.DESIGN)
    jobs = FakeJobRepository([job])
    specs = FakeSpecs()
    specs.value = _synthesized_spec()

    def handler() -> DesignSpecHandler:
        return DesignSpecHandler(specs=specs)

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {"spec": specs.value, "published": specs.published},
    )


# ------------------------------------------------------------------------ review_collect


def _review_collect(answer: dict[str, object] | None) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("review.collect", Phase.REVIEW, project_id)
        jobs = FakeJobRepository([job])
        gates = FakeHumanGateRepository()
        ledger = PhaseEntries(Phase.REVIEW)

        def handler() -> ReviewCollectHandler:
            return ReviewCollectHandler(ledger=ledger, gates=gates, jobs=jobs, clock=_Clock())

        async def answered() -> None:
            assert answer is not None
            await _park_then_answer(handler(), gates, job, answer)

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            prepare=answered if answer is not None else None,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "gates": _gates_content(gates),
            },
        )

    return build


# --------------------------------------------------------------------------- review_demo


def _review_demo(*, reviewer: bool) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        job = _job(
            "review.demo",
            Phase.REVIEW,
            payload={"run_commands": ["make run"], "summary": "what was built"},
        )
        jobs = FakeJobRepository([job])
        ledger = PhaseEntries(Phase.REVIEW)
        artifacts = FakeReviewArtifactWriter()
        found = (
            AutomatedFinding(
                category="security", text="a secret in the diff", severity=Severity.HIGH
            ),
        )

        def handler() -> ReviewDemoHandler:
            return ReviewDemoHandler(
                specs=FakeSpecRepository(_notes_spec()),
                ledger=ledger,
                artifacts=artifacts,
                jobs=jobs,
                clock=_Clock(),
                automated_reviewer=_FixedReviewer(found) if reviewer else None,
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                # The same paths are written again with the same content: an overwrite.
                "artifacts": dict(artifacts.written),
                "executable": sorted(set(artifacts.executables)),
            },
        )

    return build


# ------------------------------------------------------------- review_deployment_choice


def _deployment_choice(
    answer: dict[str, object] | None,
    *,
    config: dict[str, object] | None = None,
    replay_is_noop: bool = True,
) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("review.deployment_choice", Phase.REVIEW, project_id)
        jobs = FakeJobRepository([job])
        gates = FakeHumanGateRepository()
        ledger = PhaseEntries(Phase.REVIEW)
        projects = CasProjects(project_id, Phase.REVIEW, replay_is_noop=replay_is_noop)
        projects.project = replace(projects.project, config=config or {})

        def handler() -> ReviewDeploymentChoiceHandler:
            return ReviewDeploymentChoiceHandler(
                ledger=ledger, gates=gates, jobs=jobs, projects=projects, clock=_Clock()
            )

        async def answered() -> None:
            assert answer is not None
            await _park_then_answer(handler(), gates, job, answer)

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            prepare=answered if answer is not None else None,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "gates": _gates_content(gates),
                "project": projects.standing(),
            },
        )

    return build


# ----------------------------------------------------------------------- review_publish


def _review_publish(
    mode: str, answer: dict[str, object] | None, *, replay_is_noop: bool
) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("review.publish", Phase.REVIEW, project_id)
        jobs = FakeJobRepository([job])
        gates = FakeHumanGateRepository()
        ledger = PhaseEntries(Phase.REVIEW)
        projects = CasProjects(project_id, Phase.REVIEW, replay_is_noop=replay_is_noop)
        projects.project = replace(projects.project, config={"publish": {"mode": mode}})
        publisher = _Publisher()

        def handler() -> ReviewPublishHandler:
            return ReviewPublishHandler(
                ledger=ledger,
                gates=gates,
                projects=projects,  # type: ignore[arg-type]
                specs=_Specs(_spec()),  # type: ignore[arg-type]
                publisher=publisher,
            )

        async def answered() -> None:
            assert answer is not None
            await _park_then_answer(handler(), gates, job, answer)

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            prepare=answered if answer is not None else None,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "gates": _gates_content(gates),
                "project": projects.standing(),
                # The plans pushed, not how many times: a retry "finishes the work instead
                # of repeating it" is the publisher's contract (PublisherInterface;
                # PublishResult.already_there). The fake publisher logs calls; it does not
                # model that, so a repeated identical plan is not read as a second push.
                "published": sorted({repr(plan) for plan in publisher.published}),
                "inspected": sorted({repr(call) for call in publisher.inspected}),
            },
        )

    return build


# ----------------------------------------------------------------------- review_triage


def _review_triage(*, findings: bool, replay_is_noop: bool) -> Callable[[Path], ReplayRig]:
    def build(scratch: Path) -> ReplayRig:
        project_id = uuid4()
        job = _job("review.triage", Phase.REVIEW, project_id)
        jobs = FakeJobRepository([job])
        seeded = (
            [
                PhaseEntries.event(
                    Phase.REVIEW,
                    EventKind.FINDING_RAISED,
                    {
                        "finding_id": "f-1",
                        "text": "Trim leading and trailing whitespace on note title during save.",
                    },
                    project_id,
                )
            ]
            if findings
            else []
        )
        ledger = PhaseEntries(Phase.REVIEW, seeded=seeded)
        projects = CasProjects(project_id, Phase.REVIEW, replay_is_noop=replay_is_noop)
        specs = SpecBook(_notes_spec())

        def handler() -> ReviewTriageHandler:
            return ReviewTriageHandler(
                ledger=ledger,
                specs=specs,
                jobs=jobs,
                clock=_Clock(),
                projects=projects,
                spec_store=specs,  # type: ignore[arg-type]
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
                "project": projects.standing(),
                "carried_specs": dict(specs.saved),
            },
        )

    return build


# ----------------------------------------------------------------------------- visual


def _visual_inventory(scratch: Path) -> ReplayRig:
    job = _job("visual.inventory", Phase.VISUAL_DESIGN)
    jobs = FakeJobRepository([job])
    ledger = DesignEntries()
    inventories = FakeInventories()

    def handler() -> VisualInventoryHandler:
        return VisualInventoryHandler(
            ledger=ledger,
            producer=FakeProducer(inventory()),
            inventories=inventories,
            jobs=jobs,
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": ledger.after_delivery(),
            "jobs": jobs_content(jobs, job.id),
            "inventory": inventories.value,
        },
    )


def _visual_plan(scratch: Path) -> ReplayRig:
    job = _job("visual.plan", Phase.VISUAL_DESIGN)
    jobs = FakeJobRepository([job])
    inventories = FakeInventories()
    inventories.value = inventory()

    def handler() -> VisualPlanHandler:
        return VisualPlanHandler(inventories=inventories)

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {"inventory": inventories.value, "published": inventories.published},
    )


# The census (tests/meta/test_every_handler_has_a_replay_case.py) reads `kind="..."` of each
# ReplayCase( call inside the `CASES = (...)` of a test_*_replay.py by AST, so a kind is a
# string literal, not a variable, and a case only counts if it is in CASES and CASES is what
# the parametrized test below runs.
CASES = (
    ReplayCase(
        name="a deployment spec waiting for a person",
        kind="deploy_acceptance",
        build=_deploy_acceptance(answered=False, replay_is_noop=True),
    ),
    ReplayCase(
        name="an accepted deployment spec grants consent and starts the execution",
        kind="deploy_acceptance",
        build=_deploy_acceptance(answered=True, replay_is_noop=True),
    ),
    ReplayCase(
        name="an answered interview enqueues the synthesis",
        kind="deploy_design",
        build=_deploy_interview,
    ),
    ReplayCase(
        name="the synthesis saves the spec and enqueues it",
        kind="deploy_design",
        build=_deploy_synthesize,
    ),
    ReplayCase(
        name="a verified deployment hands over to review",
        kind="deploy_execute",
        build=_deploy_execute(fails=False, replay_is_noop=True),
    ),
    ReplayCase(
        name="a failed deployment hands over to triage",
        kind="deploy_execute",
        build=_deploy_execute(fails=True, replay_is_noop=True),
    ),
    ReplayCase(
        name="a demo waiting for a person",
        kind="deploy_review",
        build=_deploy_review("deploy.demo", None),
    ),
    ReplayCase(
        name="an approved demo enqueues the routing",
        kind="deploy_review",
        build=_deploy_review("deploy.demo", {"verdict": "approve"}, seeded=True),
    ),
    ReplayCase(
        name="an answered triage enqueues the routing",
        kind="deploy_review",
        build=_deploy_review("deploy.triage", {"choice": "RETRY_DEPLOY_EXECUTE"}, seeded=True),
    ),
    ReplayCase(
        name="a research result is recorded as untrusted",
        kind="design_research",
        build=_design_research(gap=False),
    ),
    ReplayCase(
        name="an unavailable research records a gap",
        kind="design_research",
        build=_design_research(gap=True),
    ),
    ReplayCase(
        name="a synthesized spec states the gaps", kind="design_synthesis", build=_design_synthesize
    ),
    ReplayCase(name="a spec is published", kind="design_synthesis", build=_design_spec),
    ReplayCase(
        name="a review waiting for a verdict",
        kind="review_collect",
        build=_review_collect(None),
    ),
    ReplayCase(
        name="an accepted review enqueues the triage",
        kind="review_collect",
        build=_review_collect({"verdict": "accept"}),
    ),
    ReplayCase(
        name="requested changes become findings",
        kind="review_collect",
        build=_review_collect({"verdict": "changes", "feedback": ["fix the title", "add a test"]}),
    ),
    ReplayCase(name="the demo artifacts", kind="review_demo", build=_review_demo(reviewer=False)),
    ReplayCase(
        name="a deployment choice waiting for a person",
        kind="review_deployment_choice",
        build=_deployment_choice(None),
    ),
    ReplayCase(
        name="declining deployment finishes the project locally",
        kind="review_deployment_choice",
        build=_deployment_choice({"choice": "local_only"}),
    ),
    ReplayCase(
        name="opting in hands over to deploy design",
        kind="review_deployment_choice",
        build=_deployment_choice({"choice": "deploy"}),
    ),
    ReplayCase(
        name="declining deployment on a project that publishes hands over to publishing",
        kind="review_deployment_choice",
        build=_deployment_choice({"choice": "local_only"}, config={"publish": {"mode": "auto"}}),
    ),
    ReplayCase(
        name="auto publishing finishes the project",
        kind="review_publish",
        build=_review_publish("auto", None, replay_is_noop=True),
    ),
    ReplayCase(
        name="a publish interview waiting for a person",
        kind="review_publish",
        build=_review_publish("interview", None, replay_is_noop=True),
    ),
    ReplayCase(
        name="an accepted publish interview publishes",
        kind="review_publish",
        build=_review_publish("interview", {"choice": "accept_defaults"}, replay_is_noop=True),
    ),
    ReplayCase(
        name="a review without findings routes to the deployment choice",
        kind="review_triage",
        build=_review_triage(findings=False, replay_is_noop=True),
    ),
    ReplayCase(
        name="clear findings loop back to build",
        kind="review_triage",
        build=_review_triage(findings=True, replay_is_noop=True),
    ),
    ReplayCase(name="the inventory and its plan job", kind="visual", build=_visual_inventory),
    ReplayCase(name="the published plan", kind="visual", build=_visual_plan),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.kind}: {case.name}")
async def test_a_redelivered_job_leaves_what_one_delivery_left(
    case: ReplayCase, tmp_path: Path
) -> None:
    await assert_replay_is_idempotent(case, tmp_path)


# Findings: replays that do NOT leave what one delivery left. Each is a strict xfail naming
# the finding, so a fix has to remove the mark in the same change (an unexpected pass fails),
# and none is normalised away in the cases above.
#
# F-8-1: a handler that moves the project's phase makes a compare-and-set, and the real
# repository raises ValueError when the project is no longer in the expected phase. After a
# complete delivery (a worker that died between the transition and the ack, or a lease that
# lapsed under a slow handler) the redelivery therefore raises at the transition instead of
# finishing, and the job fails although its work is done. build_integrate suppresses exactly
# this ValueError for that reason (``_maybe_enter_review``); these handlers do not.
#
# F-8-2: review.demo with an automated reviewer is a fresh scan on every delivery. It
# supersedes the earlier scan's findings and raises the same findings again under new ids
# (the production runner sets no finding id, so each is minted from a uuid4), so a redelivery
# leaves a RESOLVED twin of every automated finding in the ledger and in deltas.md. The OPEN
# set is the same; the record the reviewer reads is not. Minting a stable id is NOT the fix: a
# FindingRaised after its own FindingResolved reads as resolved (projections.build_deltas), so
# a stable id would make the supersede hide the live finding.
#
# (F-8-3, review.collect minting a requested change's finding id from a fresh uuid4 so that a
# redelivery raised every change a second time, is fixed: its case is in CASES.)
def _known(
    finding: str, build: Callable[[Path], ReplayRig], raises: type[Exception], name: str
) -> Any:
    return pytest.param(
        build,
        id=name,
        marks=pytest.mark.xfail(
            strict=True, raises=raises, reason=f"{finding}: see the note above KNOWN_FINDINGS"
        ),
    )


KNOWN_FINDINGS = (
    _known(
        "F-8-1",
        _deploy_acceptance(answered=True, replay_is_noop=False),
        ValueError,
        "F-8-1 deploy_acceptance",
    ),
    _known(
        "F-8-1",
        _deploy_execute(fails=False, replay_is_noop=False),
        ValueError,
        "F-8-1 deploy_execute (verified)",
    ),
    _known(
        "F-8-1",
        _deploy_execute(fails=True, replay_is_noop=False),
        ValueError,
        "F-8-1 deploy_execute (failed)",
    ),
    _known(
        "F-8-1",
        _deployment_choice({"choice": "deploy"}, replay_is_noop=False),
        ValueError,
        "F-8-1 review_deployment_choice (deploy)",
    ),
    _known(
        "F-8-1",
        _deployment_choice({"choice": "local_only"}, replay_is_noop=False),
        ValueError,
        "F-8-1 review_deployment_choice (local)",
    ),
    _known(
        "F-8-1",
        _review_publish("auto", None, replay_is_noop=False),
        ValueError,
        "F-8-1 review_publish",
    ),
    _known(
        "F-8-1",
        _review_triage(findings=True, replay_is_noop=False),
        ValueError,
        "F-8-1 review_triage",
    ),
    _known(
        "F-8-2", _review_demo(reviewer=True), AssertionError, "F-8-2 review_demo (automated review)"
    ),
)


@pytest.mark.parametrize("build", KNOWN_FINDINGS)
async def test_a_known_finding(build: Callable[[Path], ReplayRig], tmp_path: Path) -> None:
    case = ReplayCase(name="a known finding", kind="finding", build=build)
    await assert_replay_is_idempotent(case, tmp_path)


def test_every_case_defined_here_is_run() -> None:
    defined = [value for value in globals().values() if isinstance(value, ReplayCase)]
    assert defined == []  # no stray module-level case outside CASES
    assert len(CASES) == len({(case.kind, case.name) for case in CASES})
