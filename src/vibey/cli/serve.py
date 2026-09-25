# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey serve`: the hub, the one HTTP surface every Krypton client reaches (ADR-0067).

It listens on the loopback interface unless `vibey.toml` declares `[hub] lan = true`, and
refuses to start on any other address without that declaration (exit 2). Every route is
under `/api/v1`, answers only a `Host` it expects, and names its caller before it runs:
the host's own programs present the token in the hub's state directory (printed at
start); devices on the network pair (ADR-0067's pairing, a later change).

Everything it says comes from the services and presenters the CLI already uses -- the
documents are the ones `--json` prints -- so a client reads one contract whichever way
it asks (doctrine 7). `vibey serve --openapi` prints the OpenAPI 3.1 document and exits,
with no database; it is committed at `docs/reference/hub-api.json`.

This module is the composition for the hub: it is the one layer that may reach the CLI's
presenters, the TUI's dashboard read and the infrastructure together.
"""

import asyncio
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Annotated, Final, cast
from uuid import UUID

import typer

from vibey.application.dto import (
    GateAnswerOutcome,
    HumanGateRecord,
    ProjectBudget,
    ProjectRecord,
    QueueEntry,
)
from vibey.application.hub.hub_service import HubService
from vibey.application.hub.interfaces.hub_service_interface import (
    HubDocument,
    HubServiceInterface,
)
from vibey.bootstrap import AppResources, build_app
from vibey.cli.budget import BUDGET_PRESENTER
from vibey.cli.errors import EXIT_USAGE
from vibey.cli.gates import GATES_PRESENTER
from vibey.cli.interfaces.budget_interface import BudgetPresenterInterface
from vibey.cli.interfaces.gates_interface import GatesPresenterInterface
from vibey.cli.interfaces.ledger_search_interface import LedgerSearchPresenterInterface
from vibey.cli.interfaces.loops_interface import LoopsCommandInterface, LoopsPresenterInterface
from vibey.cli.interfaces.projects_interface import ProjectsPresenterInterface
from vibey.cli.interfaces.queue_interface import QueuePresenterInterface
from vibey.cli.interfaces.serve_interface import ServeCommandInterface
from vibey.cli.interfaces.status_interface import StatusPresenterInterface
from vibey.cli.ledger_search import PRESENTER as LEDGER_PRESENTER
from vibey.cli.loops import LOOPS, LOOPS_PRESENTER
from vibey.cli.projects import PROJECTS_PRESENTER
from vibey.cli.queue import QUEUE_PRESENTER
from vibey.cli.status import STATUS_PRESENTER
from vibey.domain.config import ConfigError
from vibey.domain.hub_binding import HUB_BINDING, UndeclaredExposure
from vibey.domain.interfaces.hub_binding_interface import HubBindingPolicyInterface
from vibey.domain.interfaces.ledger_query_interface import LedgerSearchResultInterface
from vibey.domain.interfaces.queue_priority_interface import PriorityChangeInterface
from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository
from vibey.infrastructure.db.ledger_search_repository import PostgresLedgerSearchRepository
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS
from vibey.infrastructure.hub.app import HUB_APP
from vibey.infrastructure.hub.authenticator import LocalTokenAuthenticator
from vibey.infrastructure.hub.exposure import HUB_EXPOSURE
from vibey.infrastructure.hub.interfaces.app_interface import HubAppFactoryInterface
from vibey.infrastructure.hub.interfaces.exposure_interface import HubExposureCheckInterface
from vibey.infrastructure.hub.interfaces.lanes_interface import LaneScannerInterface
from vibey.infrastructure.hub.interfaces.server_interface import (
    HubServerInterface,
    LocalNamesInterface,
)
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.lanes import LaneEngine, LaneScanner
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.server import HUB_SERVER, LOCAL_NAMES
from vibey.infrastructure.hub.settings import HUB_SETTINGS, HubSettings
from vibey.tui.dashboard import fetch_dashboard_state

DOCTOR_SCOPE: Final = "the checks the hub runs itself; `vibey doctor` on the host is the full check"
"""What the hub's doctor document says about its own reach (10.f)."""


class CliHubDocuments:
    """The hub's documents, from the presenters the CLI's `--json` prints through.

    Declared by `HubDocumentsInterface` (application/hub/interfaces)."""

    def __init__(
        self,
        *,
        projects: ProjectsPresenterInterface = PROJECTS_PRESENTER,
        gates: GatesPresenterInterface = GATES_PRESENTER,
        budget: BudgetPresenterInterface = BUDGET_PRESENTER,
        queue: QueuePresenterInterface = QUEUE_PRESENTER,
        ledger: LedgerSearchPresenterInterface = LEDGER_PRESENTER,
    ) -> None:
        self._projects = projects
        self._gates = gates
        self._budget = budget
        self._queue = queue
        self._ledger = ledger

    def projects(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> HubDocument:
        return json.loads(self._projects.projects_json(projects, open_gates))

    def gates(self, gates: Sequence[HumanGateRecord], names: Mapping[UUID, str]) -> HubDocument:
        return json.loads(self._gates.gates_json(gates, names))

    def answered(self, outcome: GateAnswerOutcome) -> HubDocument:
        record = outcome.record
        return {
            "gate_id": str(record.gate_id),
            "project_id": str(record.project_id),
            "kind": record.kind,
            "answer": dict(record.answer) if record.answer is not None else None,
            "answered_by": record.answered_by,
            "answered_at": record.answered_at.isoformat() if record.answered_at else None,
            "request_id": record.answer_request_id,
            "replayed": outcome.replayed,
        }

    def budget(self, budget: ProjectBudget) -> HubDocument:
        return self._budget.document(budget)

    def queue(self, project_id: UUID, entries: Sequence[QueueEntry]) -> HubDocument:
        return json.loads(self._queue.entries_json(project_id, entries))

    def bumped(self, change: PriorityChangeInterface) -> HubDocument:
        return json.loads(self._queue.change_json(change))

    def ledger(self, project_id: UUID, result: LedgerSearchResultInterface) -> HubDocument:
        return json.loads(self._ledger.machine(project_id, result))


class CliHubProbes:
    """The reads composed above the application layer: status through the TUI's
    dashboard read, loops through `vibey loops`, lanes and the hub's own checks.

    Declared by `HubProbesInterface` (application/hub/interfaces)."""

    def __init__(
        self,
        *,
        resources: AppResources,
        settings: HubSettings,
        store: LocalTokenStore,
        lanes: LaneScannerInterface,
        loops: LoopsCommandInterface = LOOPS,
        loops_presenter: LoopsPresenterInterface = LOOPS_PRESENTER,
        status: StatusPresenterInterface = STATUS_PRESENTER,
        exposure: HubExposureCheckInterface = HUB_EXPOSURE,
    ) -> None:
        self._resources = resources
        self._settings = settings
        self._store = store
        self._lanes = lanes
        self._loops = loops
        self._loops_presenter = loops_presenter
        self._status = status
        self._exposure = exposure

    async def status(self, project_id: UUID) -> HubDocument:
        resources = self._resources
        state = await fetch_dashboard_state(
            projects=resources.projects,
            jobs=resources.jobs,
            health=PostgresEngineHealthRepository(resources.ledger._pool),
            ledger=resources.ledger,
            project_id=project_id,
        )
        return self._status.document(state)

    def loops(self) -> HubDocument:
        return json.loads(self._loops_presenter.json(self._loops.report()))

    def lanes(self) -> HubDocument:
        return {"lanes": self._lanes.lanes()}

    async def doctor(self) -> HubDocument:
        database = await self.ready()
        exposure = self._exposure.run(self._settings, self._store)
        return {
            "scope": DOCTOR_SCOPE,
            "checks": [
                {
                    "name": "database",
                    "mark": "PASS" if database else "FAIL",
                    "detail": "the database answers"
                    if database
                    else "the database does not answer",
                },
                {"name": "hub-exposure", "mark": exposure.mark, "detail": exposure.detail},
            ],
        }

    async def ready(self) -> bool:
        """True when the database answers a read."""
        try:
            await self._resources.projects.get_latest()
        except Exception:  # noqa: BLE001 - any failure to read is "not ready", said as such
            return False
        return True


class ServeCommand:
    """Resolves where to listen, opens vibey, builds the hub, serves until stopped.

    Declared by `interfaces/serve_interface.py::ServeCommandInterface`."""

    def __init__(
        self,
        *,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        factory: HubAppFactoryInterface = HUB_APP,
        binding: HubBindingPolicyInterface = HUB_BINDING,
        server: HubServerInterface = HUB_SERVER,
        names: LocalNamesInterface = LOCAL_NAMES,
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        now: Callable[[], float] = time.time,
        exposure: HubExposureCheckInterface = HUB_EXPOSURE,
    ) -> None:
        self._exposure = exposure
        self._open_app = open_app
        self._settings = settings
        self._factory = factory
        self._binding = binding
        self._server = server
        self._names = names
        self._config_path = config_path
        self._now = now

    def openapi(self) -> str:
        """The OpenAPI 3.1 document, with no database: building the app calls no route,
        so the service it is built over is never asked anything."""
        app = self._factory.build(
            cast(HubServiceInterface, None),
            authenticator=LocalTokenAuthenticator("unused"),
            allowed_hosts=frozenset(),
            ready=self._never_ready,
        )
        return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"

    async def run(self, *, host: str | None, port: int | None) -> None:
        settings = self._settings.load(self._config_path())
        try:
            bound = self._binding.resolve(host, lan_declared=settings.lan)
        except UndeclaredExposure as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(EXIT_USAGE) from exc
        listen = port if port is not None else settings.port
        store = LocalTokenStore(settings.state_dir)
        token = store.token()
        names = self._names.names(bound) | settings.names if settings.lan else frozenset()
        allowed = self._binding.allowed_hosts(listen, names)
        scanner = LaneScanner(
            engines=[LaneEngine(d.engine_id.value, d.state_dir) for d in ALL_DESCRIPTORS],
            roots=settings.lane_roots or (self._config_path().parent,),
            now=self._now,
        )
        async with self._open_app() as resources:
            probes = CliHubProbes(
                resources=resources, settings=settings, store=store, lanes=scanner
            )
            service = HubService(
                projects=resources.projects,
                gates=resources.gates,
                gate_answers=resources.gate_answers,
                budgets=resources.project_budgets,
                queue=resources.queue_priority,
                ledger=PostgresLedgerSearchRepository(resources.ledger._pool),
                documents=CliHubDocuments(),
                probes=probes,
            )
            app = self._factory.build(
                service,
                authenticator=LocalTokenAuthenticator(token),
                allowed_hosts=allowed,
                ready=probes.ready,
            )
            typer.echo(f"vibey hub on http://{self._shown(bound)}:{listen}/api/v1")
            typer.echo(f"host token: {settings.state_dir / 'token'} (owner-only)")
            store.record_serving(ServingRecord(host=bound, port=listen, pid=os.getpid()))
            try:
                await self._server.serve(app, host=bound, port=listen)
            finally:
                store.clear_serving()

    def exposure_line(self) -> bool:
        """`vibey doctor`'s `hub-exposure` line, printed; False only on FAIL. A `[hub]`
        table that cannot be read is a FAIL: no declaration can be judged against it."""
        try:
            settings = self._settings.load(self._config_path())
        except ConfigError as exc:
            typer.echo(f"FAIL {'hub-exposure':<20} {exc}")
            return False
        finding = self._exposure.run(settings, LocalTokenStore(settings.state_dir))
        typer.echo(f"{finding.mark} {'hub-exposure':<20} {finding.detail}")
        return finding.ok

    @staticmethod
    def _shown(host: str) -> str:
        return f"[{host}]" if ":" in host else host

    @staticmethod
    async def _never_ready() -> bool:
        return False


SERVE: Final[ServeCommandInterface] = ServeCommand()
"""The command `vibey serve` runs. Annotated with the interface so `mypy --strict` checks
the class against its declared seam."""


def serve(
    host: Annotated[
        str | None,
        typer.Option(
            "--host",
            help="Address to listen on. Default loopback (127.0.0.1); any other address "
            "needs [hub] lan = true in vibey.toml.",
        ),
    ] = None,
    port: Annotated[
        int | None,
        typer.Option("--port", help="Port to listen on. Default [hub] port, else 8765."),
    ] = None,
    openapi: Annotated[
        bool,
        typer.Option("--openapi", help="Print the OpenAPI 3.1 document and exit; no database."),
    ] = False,
) -> None:
    """Serve the hub: the HTTP API every Krypton client reaches, loopback by default."""
    # A module-level function because typer builds the command from a plain function's
    # signature. It holds no logic; the command class does.
    if openapi:
        typer.echo(SERVE.openapi(), nl=False)
        return
    asyncio.run(SERVE.run(host=host, port=port))
