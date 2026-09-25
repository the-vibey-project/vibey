# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's use cases: every read and every action a Krypton client can ask for.

`vibey serve` (ADR-0067) exposes these over HTTP. Each use case does three things, in
this order, and nothing else:

1. **Authorise.** The principal's scopes are checked against the action through the one
   domain policy (`domain/hub_scope.py`), before anything is read. Deny by default.
2. **Delegate.** The work goes to the service or repository the CLI already uses --
   answering through `GateAnswerService` (the compare-and-set of #1147), bumping through
   `QueuePriorityService` (its grant, ADR-0054), budgets through `ProjectBudgetService`
   read-only. The hub owns no query and no write of its own, so it cannot drift from the
   CLI and cannot route around a check the CLI makes.
3. **Render.** The result becomes a document through `HubDocumentsInterface`, which
   `vibey serve` builds from the CLI's own presenters: one JSON contract for both.

A bump is always requested as the declared queue source `HUB_QUEUE_SOURCE`, so the host's
`vibey.toml` decides whether the hub may reorder at all (`[queue.priority] sources`); a
device's `bump` scope is necessary and never sufficient.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Final
from uuid import UUID

from vibey.application.dto import HubPrincipal, ProjectRecord
from vibey.application.hub.interfaces.hub_service_interface import (
    HubDocument,
    HubDocumentsInterface,
    HubProbesInterface,
)
from vibey.application.interfaces.gate_answer import GateAnswerServiceInterface
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.ledger import LedgerSearch
from vibey.application.interfaces.project_budget import ProjectBudgetServiceInterface
from vibey.application.interfaces.projects import ProjectReader
from vibey.application.interfaces.queue_priority import QueuePriorityServiceInterface
from vibey.domain.errors import UnknownGate, UnknownProject
from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubForbidden
from vibey.domain.interfaces.hub_scope_interface import HubScopePolicyInterface
from vibey.domain.interfaces.ledger_query_interface import (
    ActorResolverInterface,
    EventKindResolverInterface,
)
from vibey.domain.ledger_query import ACTORS, EVENT_KINDS, LedgerQuery

HUB_QUEUE_SOURCE: Final = "vibey-hub"
"""The queue source every hub bump is requested as. The host admits it, or not, in
`[queue.priority] sources` (ADR-0054)."""


class HubService:
    """Declared by `interfaces/hub_service_interface.py::HubServiceInterface`."""

    def __init__(
        self,
        *,
        projects: ProjectReader,
        gates: HumanGateRepository,
        gate_answers: GateAnswerServiceInterface,
        budgets: ProjectBudgetServiceInterface,
        queue: QueuePriorityServiceInterface,
        ledger: LedgerSearch,
        documents: HubDocumentsInterface,
        probes: HubProbesInterface,
        policy: HubScopePolicyInterface = HUB_SCOPES,
        kinds: EventKindResolverInterface = EVENT_KINDS,
        actors: ActorResolverInterface = ACTORS,
    ) -> None:
        self._projects = projects
        self._gates = gates
        self._gate_answers = gate_answers
        self._budgets = budgets
        self._queue = queue
        self._ledger = ledger
        self._documents = documents
        self._probes = probes
        self._policy = policy
        self._kinds = kinds
        self._actors = actors

    async def projects(self, principal: HubPrincipal) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        projects = await self._projects.list_all()
        gates = await self._gates.open_all()
        return self._documents.projects(projects, Counter(gate.project_id for gate in gates))

    async def status(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        await self._project(project_id)
        return await self._probes.status(project_id)

    async def gates(self, principal: HubPrincipal, project_id: UUID | None) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        projects: Sequence[ProjectRecord]
        if project_id is None:
            # Gates first: a gate never outlives its project (ON DELETE CASCADE), so every
            # project a gate read here names is still there to be read next.
            gates = await self._gates.open_all()
            projects = await self._projects.list_all()
        else:
            projects = (await self._project(project_id),)
            gates = await self._gates.open_for_project(project_id)
        names = {project.project_id: project.name for project in projects}
        listed = tuple(gate for gate in gates if gate.project_id in names)
        return self._documents.gates(listed, names)

    async def answer_gate(
        self,
        principal: HubPrincipal,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        request_id: str | None,
    ) -> HubDocument:
        # `answer` is the least any answer needs; a spending gate needs `spend` too, and
        # that is only known once the gate's kind is read -- so check twice.
        self._authorise(principal, HubAction.ANSWER_GATE)
        gate = next(
            (open_ for open_ in await self._gates.open_all() if open_.gate_id == gate_id), None
        )
        if gate is not None:
            self._authorise(principal, self._policy.action_for_gate(gate.kind))
        elif request_id is None:
            # Not open. With a request id it may be this request's own earlier answer, which
            # the service replays; without one there is nothing it could do but refuse.
            raise UnknownGate(f"no open gate {gate_id}")
        outcome = await self._gate_answers.answer(
            gate_id, answer, by=principal.name, request_id=request_id
        )
        return self._documents.answered(outcome)

    async def budget(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        await self._project(project_id)
        return self._documents.budget(await self._budgets.show(project_id))

    async def queue(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        await self._project(project_id)
        return self._documents.queue(project_id, await self._queue.queue(project_id))

    async def bump(self, principal: HubPrincipal, project_id: UUID, job_id: UUID) -> HubDocument:
        self._authorise(principal, HubAction.BUMP_JOB)
        await self._project(project_id)
        change = await self._queue.bump(project_id, job_id, source=HUB_QUEUE_SOURCE)
        return self._documents.bumped(change)

    async def ledger(
        self,
        principal: HubPrincipal,
        project_id: UUID,
        *,
        text: str | None,
        kinds: Sequence[str],
        actor: str | None,
        limit: int,
    ) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        query = LedgerQuery(
            actor=None if actor is None else self._actors.resolve(actor),
            kinds=frozenset(self._kinds.resolve(label) for label in kinds),
            text=text,
            limit=limit,
        )
        await self._project(project_id)
        return self._documents.ledger(project_id, await self._ledger.search(project_id, query))

    def loops(self, principal: HubPrincipal) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        return self._probes.loops()

    def lanes(self, principal: HubPrincipal) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        return self._probes.lanes()

    async def doctor(self, principal: HubPrincipal) -> HubDocument:
        self._authorise(principal, HubAction.READ)
        return await self._probes.doctor()

    def _authorise(self, principal: HubPrincipal, action: HubAction) -> None:
        if not self._policy.permits(principal.scopes, action):
            raise HubForbidden(f"{principal.name} may not {action.value}")

    async def _project(self, project_id: UUID) -> ProjectRecord:
        project = await self._projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        return project
