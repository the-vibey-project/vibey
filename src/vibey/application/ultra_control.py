# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every ULTRA control takes (ADR-0063, sub-doctrine 8.b's no-cap path).

`start` and `stop` record the operator's controls; the BUILD handler reads the latest of
them at every pass, so Stop binds at the next pass boundary. `declare_no_cap` records
the declaration once the caller has shown both warnings and the person typed the phrase;
the phrase is checked here too, so no entry point can record it without one.
`keep_cap` withdraws it in one action.

Every event names who (`by`, a label, and `account`, the operating system's name for
whoever ran it), when, and which device -- the host's name. A phone or the web app is
never a device here: this service is reached only from the host's own CLI.
"""

from uuid import UUID

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.dto import UltraStatus
from vibey.application.interfaces import CallerIdentity, Clock, LedgerReader, ProjectReader
from vibey.application.interfaces.ultra_control import UltraControlStore
from vibey.application.project_budget import LedgerSnapshot
from vibey.domain.budget_caps import CAP_CHANGE_PLANNER
from vibey.domain.errors import InvalidBudgetChange, UnknownProject
from vibey.domain.interfaces.budget_caps_interface import CapChangePlannerInterface
from vibey.domain.interfaces.ultra_interface import UltraPolicyInterface
from vibey.domain.ledger import EventKind
from vibey.domain.ultra import NO_CAP_PHRASE, ULTRA_POLICY


class UltraControlService:
    """Declared by `interfaces/ultra_control.py::UltraControlServiceInterface`."""

    def __init__(
        self,
        *,
        projects: ProjectReader,
        ledger: LedgerReader,
        store: UltraControlStore,
        caller: CallerIdentity,
        clock: Clock,
        device: str,
        policy: UltraPolicyInterface = ULTRA_POLICY,
        planner: CapChangePlannerInterface = CAP_CHANGE_PLANNER,
    ) -> None:
        self._projects = projects
        self._ledger = ledger
        self._store = store
        self._caller = caller
        self._clock = clock
        self._device = device
        self._policy = policy
        self._planner = planner

    async def status(self, project_id: UUID) -> UltraStatus:
        project = await self._projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        events = await self._ledger.all_for_project(project_id)
        state = self._policy.state(events)
        max_dollars, max_turns = LedgerBudgetSource.caps_from_config(project.config)
        budget = await LedgerBudgetSource(
            LedgerSnapshot(events), max_dollars=max_dollars, max_turns=max_turns
        ).current(project_id, project.cycle)
        return UltraStatus(
            project_id=project_id,
            name=project.name,
            active=state.active,
            no_cap_declared=state.no_cap_declared,
            # Distinct (item, pass): a replayed pass may append its event twice.
            passes_completed=len(
                {
                    (event.payload.get("work_item_id"), event.payload.get("pass"))
                    for event in events
                    if event.kind is EventKind.ULTRA_PASS_COMPLETED
                }
            ),
            max_dollars=budget.max_dollars,
            dollars_spent=budget.dollars_spent,
            rate_per_hour=self._policy.rate_per_hour(events),
        )

    async def start(self, project_id: UUID, *, by: str | None = None) -> UltraStatus:
        return await self._record(project_id, EventKind.ULTRA_STARTED, {}, by)

    async def stop(self, project_id: UUID, *, by: str | None = None) -> UltraStatus:
        return await self._record(project_id, EventKind.ULTRA_STOPPED, {}, by)

    async def declare_no_cap(
        self, project_id: UUID, *, phrase: str, by: str | None = None
    ) -> UltraStatus:
        if not self._policy.phrase_matches(phrase):
            raise InvalidBudgetChange(f"no cap needs the phrase typed exactly: {NO_CAP_PHRASE}")
        return await self._record(project_id, EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": True}, by)

    async def keep_cap(self, project_id: UUID, *, by: str | None = None) -> UltraStatus:
        return await self._record(
            project_id, EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": False}, by
        )

    async def _record(
        self, project_id: UUID, kind: EventKind, payload: dict[str, object], label: str | None
    ) -> UltraStatus:
        account = self._caller.current().name
        by = self._planner.actor(label, account=account)
        await self._store.record(
            project_id,
            kind,
            {**payload, "by": by, "account": account, "device": self._device},
            at=self._clock.now(),
        )
        return await self.status(project_id)
