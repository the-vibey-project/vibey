# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's seams: what it asks of vibey, what renders its answers, and what it offers.

Mirrors `vibey/application/hub/hub_service.py` (ADR-0016, ADR-0067). Interfaces declare;
they never consume. The records the seams are declared over are imported under
TYPE_CHECKING only.

A document is what a route returns: plain JSON-able data. The hub renders every one
through `HubDocumentsInterface`, and `vibey serve` supplies the implementation from the
same presenters the CLI's `--json` prints through -- so a client reads one contract
whether it runs `vibey gates --json` or asks the hub (doctrine 7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from vibey.application.dto import (
        GateAnswerOutcome,
        HubPrincipal,
        HumanGateRecord,
        ProjectBudget,
        ProjectRecord,
        QueueEntry,
    )
    from vibey.domain.interfaces.ledger_query_interface import LedgerSearchResultInterface
    from vibey.domain.interfaces.queue_priority_interface import PriorityChangeInterface
    from vibey.domain.ledger import LedgerEvent

type HubDocument = object
"""JSON-able data: what a route returns."""


@runtime_checkable
class HubDocumentsInterface(Protocol):
    """Renders the records the hub reads into the documents the CLI's `--json` prints."""

    def projects(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> HubDocument:
        """`vibey projects --json`."""
        ...

    def gates(self, gates: Sequence[HumanGateRecord], names: Mapping[UUID, str]) -> HubDocument:
        """`vibey gates --json`."""
        ...

    def answered(self, outcome: GateAnswerOutcome) -> HubDocument:
        """What answering a gate did: the gate as it now stands, and whether it replayed."""
        ...

    def budget(self, budget: ProjectBudget) -> HubDocument:
        """`vibey budget show --json`."""
        ...

    def queue(self, project_id: UUID, entries: Sequence[QueueEntry]) -> HubDocument:
        """`vibey queue list --json`."""
        ...

    def bumped(self, change: PriorityChangeInterface) -> HubDocument:
        """`vibey queue bump --json`."""
        ...

    def ledger(self, project_id: UUID, result: LedgerSearchResultInterface) -> HubDocument:
        """`vibey ledger search --json`."""
        ...

    def events(self, project_id: UUID, events: Sequence[LedgerEvent]) -> HubDocument:
        """A page of the live feed: `{"project_id", "events", "last_seq"}`, each event as
        `vibey ledger search --json` carries it."""
        ...


@runtime_checkable
class HubProbesInterface(Protocol):
    """The reads that are composed outside the application layer: a project's status,
    the loops, the lanes on this computer, and the hub's own health checks."""

    async def status(self, project_id: UUID) -> HubDocument:
        """`vibey status --json` for one project."""
        ...

    def loops(self) -> HubDocument:
        """`vibey loops --json`."""
        ...

    def lanes(self) -> HubDocument:
        """Every lane running on this computer, as the VS Code extension lists them."""
        ...

    async def doctor(self) -> HubDocument:
        """The checks the hub runs itself; `vibey doctor` on the host is the full check."""
        ...

    def lane_tail(self, events_path: str, after: int) -> HubDocument:
        """A listed lane's complete lines after byte `after`, and the offset to resume
        from. Raises `UnknownLane` for a path that is not a listed lane."""
        ...


@runtime_checkable
class HubServiceInterface(Protocol):
    """Every use case the hub offers. Each checks the principal's scopes first and
    raises `HubForbidden` when they do not permit it, before anything is read or written;
    `UnknownProject` when the project named does not exist."""

    async def projects(self, principal: HubPrincipal) -> HubDocument:
        """Every project, newest first, with its open-gate count. Needs `view`."""
        ...

    async def status(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        """One project's phase, queue depth and engine circuits. Needs `view`."""
        ...

    async def gates(self, principal: HubPrincipal, project_id: UUID | None) -> HubDocument:
        """Open gates, every project's or one project's, oldest first. Needs `view`."""
        ...

    async def answer_gate(
        self,
        principal: HubPrincipal,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        request_id: str | None,
    ) -> HubDocument:
        """Answers a gate once through the one answering service (#1147), recorded under
        the principal's name. Needs `answer`, or `spend` for a spending gate."""
        ...

    async def budget(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        """A project's caps and spend. Read only: no route changes a cap. Needs `view`."""
        ...

    async def queue(self, principal: HubPrincipal, project_id: UUID) -> HubDocument:
        """A project's queue, claim order. Needs `view`."""
        ...

    async def bump(self, principal: HubPrincipal, project_id: UUID, job_id: UUID) -> HubDocument:
        """Moves a queued job to the front, through the queue-priority grant. Needs `bump`."""
        ...

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
        """Searches a project's ledger. Needs `view`."""
        ...

    def loops(self, principal: HubPrincipal) -> HubDocument:
        """The loops, engines and efforts. Needs `view`."""
        ...

    def lanes(self, principal: HubPrincipal) -> HubDocument:
        """The lanes on this computer. Needs `view`."""
        ...

    async def doctor(self, principal: HubPrincipal) -> HubDocument:
        """The hub's own checks. Needs `view`."""
        ...

    async def ledger_after(
        self, principal: HubPrincipal, project_id: UUID, *, after: int, limit: int
    ) -> HubDocument:
        """Up to `limit` events with seq greater than `after`, oldest first -- the live
        feed's catch-up and every page after it. A position, never a time. Needs `view`."""
        ...

    def lane_tail(self, principal: HubPrincipal, events_path: str, after: int) -> HubDocument:
        """A lane's lines after byte `after`. Needs `view`."""
        ...
