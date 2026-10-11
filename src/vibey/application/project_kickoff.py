# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starting a project's DESIGN interview, in one place.

This used to live as a private helper inside the CLI, which was fine while
the CLI was the only way in. It is not: the Kubernetes operator creates
projects from a custom resource, and runbook 05 names the failure that
follows -- a second entry point growing its own copy of the transition and
enqueue logic, which then drifts. Both callers use this function.
"""

from typing import Final
from uuid import UUID

from vibey.application.dto import EnqueueRequest, ProjectRecord
from vibey.application.interfaces.design import DesignSpecRepository
from vibey.application.interfaces.design_auto_accept import DesignAcceptorInterface
from vibey.application.interfaces.projects import ProjectStore
from vibey.application.interfaces.queue import JobRepository
from vibey.application.interfaces.queue_priority import QueuePriorityServiceInterface
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.job import idempotency_key
from vibey.domain.phase import Phase, VisualDecision
from vibey.domain.spec import DesignSpec


async def enqueue_design_interview(
    *,
    projects: ProjectStore,
    jobs: JobRepository,
    project_id: UUID,
    origin: str = "interactive",
    priority: QueuePriorityServiceInterface | None = None,
) -> UUID:
    """Move a fresh project into DESIGN and enqueue its interview.

    Idempotent through the job's idempotency key: calling it twice for the
    same project and cycle yields the same job rather than a second
    interview. That matters more for the operator than the CLI, since a
    reconcile loop will call it again every time it is unsure.

    `origin` participates in the idempotency key, so a project started from
    a custom resource and one started from the CLI are distinguishable in
    the ledger without changing behaviour.

    `priority`, when given, enqueues the interview already bumped (ADR-0054): it runs
    next, after whatever is running, through the same grant every bump passes.
    """
    project: ProjectRecord | None = await projects.get(project_id)
    if project is None:
        raise UnknownProject(f"unknown project {project_id}")
    if project.phase is Phase.INTAKE:
        project = await projects.transition(project_id, expected=Phase.INTAKE, to=Phase.DESIGN)
    if project.phase is not Phase.DESIGN:
        raise WrongPhase(f"project is in {project.phase.value}, not design")
    request = EnqueueRequest(
        project_id=project_id,
        cycle=project.cycle,
        phase=Phase.DESIGN,
        kind="design.interview",
        idempotency_key=idempotency_key(project_id, project.cycle, "design.interview", origin),
        requirement={"effort": "high"},
    )
    if priority is not None:
        job, _ = await priority.enqueue(request)
        return job.id
    return (await jobs.enqueue(request)).id


SUPPLIED_SPEC_ACTOR: Final = "new-with-spec"
"""Who the ledger says accepted a design that was supplied rather than interviewed."""


async def accept_supplied_design(
    *,
    projects: ProjectStore,
    specs: DesignSpecRepository,
    acceptor: DesignAcceptorInterface,
    project_id: UUID,
    spec: DesignSpec,
    accepted_by: str = SUPPLIED_SPEC_ACTOR,
) -> ProjectRecord:
    """Skip DESIGN: this reviewed spec is the design, so there is nothing to interview.

    A spec an operator has already reviewed makes the DESIGN interview, its research and its
    spec synthesis work whose output is thrown away: `--accept-spec-json` on a worker could only
    act once every DESIGN job had settled, so all of it ran first (a real run spent the time and
    then hung on three research gates for evidence nobody needed). Here the project moves into
    DESIGN without an interview job, the spec is saved, and it is accepted at once through
    `DesignAcceptanceService`, whose guards still apply, with the visual-design choice declined
    as every unattended acceptance declines it. BUILD's decomposition is enqueued by the
    acceptance, as for any accepted design.

    Raises ValueError when the acceptance refuses the spec (it has no acceptance criteria, for
    one); the project and the saved spec stay, so `vibey design accept PROJECT --spec-json FILE`
    can finish it once the spec is fixed.
    """
    project: ProjectRecord | None = await projects.get(project_id)
    if project is None:
        raise UnknownProject(f"unknown project {project_id}")
    if project.phase is Phase.INTAKE:
        project = await projects.transition(project_id, expected=Phase.INTAKE, to=Phase.DESIGN)
    if project.phase is not Phase.DESIGN:
        raise WrongPhase(f"project is in {project.phase.value}, not design")
    await specs.save(project_id, project.cycle, spec)
    return await acceptor.accept(
        project_id, visual_choice=VisualDecision.DECLINED, accepted_by=accepted_by
    )
