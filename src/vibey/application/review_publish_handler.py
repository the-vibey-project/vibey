# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable ``review.publish`` handler: the last step of a delivered project.

After REVIEW is accepted and the deployment choice is ``local_only``, a project whose
``[publish] mode`` is not ``off`` does not finish yet: this job gets its work off the machine
first. A checkout with a remote has its branch pushed and a pull request opened; one with no
remote gets a new GitHub repository. Then, and only then, the project is DONE.

Both leave the machine and neither is easily taken back, so:

- ``off`` (the default) never reaches here, and a job that does anyway finishes without doing
  anything.
- ``interview`` raises a ``publish_interview`` gate whose prompt says exactly what would be
  pushed and where, and waits. The gate has no default and never times out to one. An answer
  that cannot be used (a field that is not one, an option posing as a name) is not guessed at:
  a new gate says what to fix.
- ``auto`` publishes the proposal without a gate; a worker started with ``--auto-publish``
  does the same for ``interview`` by answering it ``accept_defaults``.
- A publisher that is not ready (``gh`` missing, not logged in) parks the job on an
  ``engine_misconfigured`` gate: fix it, answer anything, and it retries.

Nothing is forced, the project's default branch is never pushed to, and a retry after a
partial failure finishes the work instead of repeating it.
"""

from pathlib import Path

from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces import PhaseLedger, ProjectStore
from vibey.application.interfaces.publish import PublisherInterface
from vibey.application.ports import HumanGateRepository
from vibey.application.review_demo_handler import DesignSpecReader
from vibey.application.worker import Failure, Outcome, Park, Success
from vibey.domain.config import ConfigError, PublishConfig
from vibey.domain.job import FailureClass
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase
from vibey.domain.publish import (
    CHOICES,
    PublishAnswerError,
    PublishDecision,
    PublishFailed,
    PublishPlan,
    decide,
    default_plan,
)
from vibey.domain.worktree import WorktreeNaming

PUBLISH_INTERVIEW_GATE_KIND = "publish_interview"
"""Its answers: `{"choice": "accept_defaults" | "custom" | "skip", ...fields}`."""


class ReviewPublishHandler:
    """Declared by the worker's `JobHandler` seam; registered for ``review.publish``."""

    def __init__(
        self,
        *,
        ledger: PhaseLedger,
        gates: HumanGateRepository,
        projects: ProjectStore,
        specs: DesignSpecReader,
        publisher: PublisherInterface,
    ) -> None:
        self._ledger = ledger
        self._gates = gates
        self._projects = projects
        self._specs = specs
        self._publisher = publisher

    async def handle(self, job: JobRecord) -> Outcome:
        if job.kind != "review.publish":
            return Failure(FailureClass.VIBEY, "expected review.publish job")
        project = await self._projects.get(job.project_id)
        if project is None:
            return Failure(FailureClass.VIBEY, f"unknown project {job.project_id}")
        try:
            config = PublishConfig.from_data(project.config)
        except ConfigError as exc:
            return Failure(FailureClass.VIBEY, f"the [publish] settings are not valid: {exc}")
        if config.mode == "off":
            return await self._finish_without_publishing(job, "publishing is off")

        problem = await self._publisher.problem()
        if problem is not None:
            return Park(
                HumanGateRequest(
                    kind="engine_misconfigured",
                    prompt=(
                        f"Publishing project {project.name!r} cannot be done yet: {problem}. "
                        "Fix that, then answer anything to retry."
                    ),
                )
            )

        repo_path = Path(project.repo_path)
        try:
            target = await self._publisher.inspect(
                repo_path,
                branch=WorktreeNaming(job.project_id, job.cycle).integration_branch,
                remote=config.remote,
            )
        except PublishFailed as exc:
            return Failure(FailureClass.VIBEY, str(exc))
        spec = await self._specs.load(job.project_id, job.cycle)
        plan = default_plan(
            project_name=project.name,
            objective=spec.objective if spec is not None else "",
            criteria=tuple(c.criterion_id for c in spec.criteria) if spec is not None else (),
            cycle=job.cycle,
            target=target,
            config=config,
        )

        if config.mode == "auto":
            return await self._publish(job, plan, repo_path)
        return await self._interview(job, plan, repo_path)

    async def _interview(self, job: JobRecord, plan: PublishPlan, repo_path: Path) -> Outcome:
        gate = await self._gates.latest_for_job(job.id)
        if gate is None:
            request = self._request(plan)
            raised = await self._gates.raise_gate(job.project_id, job.id, request)
            return Park(request, gate=raised)
        if gate.answer is None:
            return Park(
                HumanGateRequest(
                    kind=gate.kind,
                    prompt=gate.prompt,
                    options=gate.options,
                    default_answer=gate.default_answer,
                )
            )
        try:
            decision = decide(plan, gate.answer)
        except PublishAnswerError as exc:
            # The last gate is answered, so the worker raises a fresh one for this request.
            return Park(self._request(plan, complaint=str(exc)))
        if decision.plan is None:
            return await self._skip(job, decision)
        return await self._publish(job, decision.plan, repo_path)

    @staticmethod
    def _request(plan: PublishPlan, *, complaint: str | None = None) -> HumanGateRequest:
        lead = f"Your answer could not be used: {complaint}.\n\n" if complaint else ""
        return HumanGateRequest(
            kind=PUBLISH_INTERVIEW_GATE_KIND,
            prompt=(
                f"{lead}The project is finished and reviewed. Publish it?\n\n"
                f"{plan.summary()}\n\n"
                "accept_defaults publishes exactly that; skip finishes the project locally; "
                "custom changes the fields you name (title, body, base, draft, visibility, "
                "repo, owner, description), e.g. --raw "
                '\'{"choice": "custom", "draft": false}\'.'
            ),
            options=CHOICES,
            # Nothing is published by silence: the declared default is the safe one.
            default_answer="skip",
        )

    async def _publish(self, job: JobRecord, plan: PublishPlan, repo_path: Path) -> Outcome:
        try:
            result = await self._publisher.publish(plan, repo_path=repo_path)
        except PublishFailed as exc:
            return Failure(FailureClass.VIBEY, f"publishing failed: {exc}")
        await self._ledger.append_event(
            job.project_id,
            job.cycle,
            job.id,
            EventKind.PUBLISH_COMPLETED,
            {
                "kind": result.kind.value,
                "url": result.url,
                "branch": plan.branch,
                "draft": plan.draft,
                "visibility": plan.visibility,
            },
        )
        await self._projects.transition(job.project_id, expected=Phase.REVIEW, to=Phase.DONE)
        return Success(
            {
                "published": True,
                "kind": result.kind.value,
                "url": result.url,
                "already_there": result.already_there,
            }
        )

    async def _skip(self, job: JobRecord, decision: PublishDecision) -> Outcome:
        return await self._finish_without_publishing(job, decision.reason)

    async def _finish_without_publishing(self, job: JobRecord, reason: str) -> Outcome:
        await self._ledger.append_event(
            job.project_id, job.cycle, job.id, EventKind.PUBLISH_SKIPPED, {"reason": reason}
        )
        await self._projects.transition(job.project_id, expected=Phase.REVIEW, to=Phase.DONE)
        return Success({"published": False, "reason": reason})
