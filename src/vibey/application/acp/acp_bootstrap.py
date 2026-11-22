# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey acp` sets up on its own when an editor first connects (SP-ACP, steps 1, 2 and 4).

`[acp] auto_bootstrap` is the operator's grant for this; with it off nothing here runs.

1. **Doctor** (`tool_call` "vibey doctor", `read`): the local doctor's checks, one
   `tool_call_update` per finished check carrying every result so far (a client replaces a tool
   call's content), then `completed`, or `failed` when a check found `FAIL`.
2. **Connect** (`tool_call` "vibey connect", `edit`), when `[acp] auto_connect` is on and the
   clients installed here are not all recorded as connected for this vibey version: `vibey mcp`
   is registered with them, never a project file and never a folder it would have to make.
3. **Services** (`tool_call` "Keep vibey's services running", `execute`), when
   `[acp] auto_services` is on and `[acp] services` names any (ADR-0101): inside the bootstrap
   lock, the units for `services` are written (`restart = [acp] restart`), never replacing one
   the operator edited, and each is loaded into the user's own service manager unless it is
   already running. A hub already running outside the service manager is left alone -- its unit
   is not loaded now, and the keep-alive takes over when it exits -- and an edited unit is
   neither loaded nor restarted. The first load says which labels were loaded and the exact
   commands that unload them. Then the hub is polled until it answers, within
   `bootstrap_timeout_seconds`. With no service manager reachable (no `gui/<uid>` domain, no
   `systemctl --user`), `vibey hub start` runs once per process instead, and the operator is
   told nothing keeps it running. What it manages is handed to the keep-alive
   (`AcpKeepAlive`), which every prompt probes first.
4. **PostgreSQL**, only inside a prompt turn and only when `[acp] install_postgres = "ask"`: when
   it is not ready, the client is asked with `session/request_permission`, and only the
   "Install PostgreSQL" option installs. "Not now", a timeout, a cancel, any other option id
   and a session that observes install nothing; once the question was asked, each of them
   closes the tool call `failed` and says once what is missing and that the hub runs degraded.
   A cancel that lands before the question leaves step 4 to the next prompt. The install runs
   `PostgresLocalService`'s fixed argv with `sudo -n`, so it never waits at a password prompt;
   a sudo that wants one is told to the operator with the command to run themselves. A cancel
   during an install the operator allowed does not stop it: the tool call is closed saying so,
   the install's end is logged (and said, if the window is still open), and the lock below is
   held until it has really ended.

Steps 1 to 3 run as one task started after `session/new` (or a load or resume) has answered,
so a slow check never delays the answer; the first prompt of each session waits for that task
within `[acp] bootstrap_timeout_seconds` and then goes ahead regardless. They never run twice at
once, never again once a run finished healthy, and run again only when a new session starts
after an unhealthy run -- never in a loop. Step 4 is asked at most once per process; its
read-only check is bounded by `bootstrap_timeout_seconds` too.

Steps 2 to 4 change the computer. Within this process they take turns (an in-process lock,
held by a worker thread that outlives its step until the thread ends); across processes they
hold `<state_dir>/acp-bootstrap.lock`, so a second editor window leaves steps 2 and 4 to the
first, and only another process holding it is reported as one. Step 3 waits for the lock within
its bound instead, then finds what the other window loaded already running. The lock file is taken and let go without an
`await` in between that a cancel could fall into.

Every text from a check, the connector or the installer is the machine's, not vibey's: it
reaches the client through `UntrustedTextInterface`, one cut line per finding. After `close`, or
for a session closed with `forget`, nothing more is sent.

Declared by `interfaces/acp_bootstrap_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, Final

from vibey.application.acp.dto import (
    AcpSessionContext,
    DoctorResult,
    PostgresInstallOutcome,
    UnitOutcome,
)
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.acp_keep_alive_interface import AcpKeepAliveInterface
from vibey.application.acp.interfaces.bootstrap_lock_interface import BootstrapLockInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.application.acp.interfaces.doctor_checks_interface import DoctorChecksInterface
from vibey.application.acp.interfaces.host_connector_interface import HostConnectorInterface
from vibey.application.acp.interfaces.postgres_installer_interface import (
    PostgresInstallerInterface,
)
from vibey.application.acp.interfaces.service_loader_interface import ServiceLoaderInterface
from vibey.application.acp.interfaces.service_units_interface import ServiceUnitsInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.modes import UnknownMode
from vibey.domain.acp.protocol import PermissionKind, ToolCallStatus, ToolKind
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_scope import HubScope
from vibey.domain.supervisor import HUB

TOOL_DOCTOR: Final = "bootstrap-doctor"
TOOL_CONNECT: Final = "bootstrap-connect"
TOOL_POSTGRES: Final = "bootstrap-postgres"
TOOL_SERVICES: Final = "bootstrap-services"
UNLOAD_COMMAND: Final = "vibey acp unload"
"""What stops and removes the units `vibey acp` loaded, for good (ADR-0101)."""
WRITTEN: Final = frozenset({"created", "unchanged", "updated"})
"""The unit file is the one vibey renders: vibey may load it and keep it running."""
INSTALL_OPTION: Final = "bootstrap-postgres:install"
NOT_NOW_OPTION: Final = "bootstrap-postgres:not-now"
INSTALL_COMMAND: Final = "vibey doctor --install-postgres"
"""What the operator runs in their own terminal when sudo wants a password."""
PACKAGE_MANAGERS: Final = frozenset({"brew", "apt-get", "dnf"})
"""The package managers `PostgresLocalService` installs with: anything else is none at all."""
POSTGRES_OPTIONS: Final[tuple[Mapping[str, str], ...]] = (
    {
        "optionId": INSTALL_OPTION,
        "name": "Install PostgreSQL",
        "kind": PermissionKind.ALLOW_ONCE.value,
    },
    {"optionId": NOT_NOW_OPTION, "name": "Not now", "kind": PermissionKind.REJECT_ONCE.value},
)
NOT_ASKED: Final = "Not asked: the prompt was cancelled first. vibey asks at your next prompt."
_LOG: Final = logging.getLogger(__name__)

type StepWait = Callable[[asyncio.Task[None], float], Awaitable[bool]]
"""Wait for the background steps up to a number of seconds; True when they finished."""
type StepTimeout = Callable[[float], AbstractAsyncContextManager[Any]]
"""The bound one step runs under (`asyncio.timeout`); it raises `TimeoutError` when it ends."""
type Sleep = Callable[[float], Awaitable[None]]


class AcpBootstrap:
    """Declared by `interfaces/acp_bootstrap_interface.py::AcpBootstrapInterface`.

    `checks`, `connector` and `postgres` are each optional: a step with nothing to run says
    nothing. Step 3 runs with `units`, `loader` and `hub` all given; `keep_alive` is told what
    it manages. `wait`, `step_timeout` and `sleep` are the clock seams (`asyncio.wait`,
    `asyncio.timeout`, `asyncio.sleep`).
    """

    def __init__(
        self,
        settings: AcpSettings,
        checks: DoctorChecksInterface[Any] | None,
        connector: HostConnectorInterface | None,
        postgres: PostgresInstallerInterface | None,
        channel: ClientChannelInterface,
        mapper: AcpUpdateMapperInterface,
        lock: BootstrapLockInterface,
        modes: AcpModesInterface,
        *,
        units: ServiceUnitsInterface | None = None,
        loader: ServiceLoaderInterface | None = None,
        hub: AcpHubPortInterface | None = None,
        keep_alive: AcpKeepAliveInterface | None = None,
        wait: StepWait | None = None,
        step_timeout: StepTimeout | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._checks = checks
        self._connector = connector
        self._postgres = postgres
        self._channel = channel
        self._mapper = mapper
        self._lock = lock
        self._modes = modes
        self._wait = wait or self._bounded_wait
        self._step_timeout: StepTimeout = step_timeout or asyncio.timeout
        self._units = units
        self._loader = loader
        self._hub = hub
        self._keep_alive = keep_alive
        self._sleep = sleep
        self._hub_started = False
        """`vibey hub start` ran once in place of a service manager: never again here."""
        self._steps: asyncio.Task[None] | None = None
        self._healthy = False
        self._waited: set[str] = set()
        """The sessions whose first prompt already waited for the background steps."""
        self._postgres_claimed = False
        """Set, with nothing awaited before it, by the one prompt running step 4 right now."""
        self._postgres_settled = False
        """Step 4 is done for this process: asked, or nothing to ask."""
        self._observe_noted = False
        self._machine = asyncio.Lock()
        """Steps 2 and 4 take turns in this process; held until a handed-over thread ends."""
        self._install_holds_machine = False
        """Set once an install the operator allowed runs: its thread lets the machine go."""
        self._late: set[asyncio.Task[None]] = set()
        self._gone: set[str] = set()
        self._closed = False

    @property
    def done(self) -> bool:
        if not self._settings.auto_bootstrap:
            return True
        postgres_left = (
            self._postgres is not None
            and self._settings.install_postgres == "ask"
            and not self._postgres_settled
        )
        return self._healthy and not postgres_left

    @property
    def steps_finished(self) -> bool:
        return self._steps is not None and self._steps.done()

    @property
    def healthy(self) -> bool:
        return self._healthy

    def start(self, session_id: str) -> None:
        if self._keep_alive is not None and self._settings.auto_bootstrap and not self._closed:
            self._keep_alive.attach(session_id)
        if not self._settings.auto_bootstrap or self._healthy or self._closed:
            return
        if self._steps is not None and not self._steps.done():
            return
        # A task of its own: the caller (session/new, load, resume) answers before the task
        # first runs, and the peer writes that answer before any update the task sends.
        self._steps = asyncio.create_task(
            self._run_steps(session_id), name=f"acp-bootstrap-{session_id}"
        )
        self._steps.add_done_callback(self._reap)

    def forget(self, session_id: str) -> None:
        self._gone.add(session_id)
        if self._keep_alive is not None:
            self._keep_alive.detach(session_id)

    async def close(self) -> None:
        self._closed = True
        if self._keep_alive is not None:
            await self._keep_alive.stop()
        running = [task for task in (self._steps, *self._late) if task is not None]
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)

    async def before_first_prompt(self, context: AcpSessionContext) -> None:
        if not self._settings.auto_bootstrap:
            return
        await self._wait_for_steps(context)
        if self._keep_alive is not None:
            # Every prompt: a hub that stopped answering is restarted before the turn needs it.
            await self._keep_alive.probe(context)
        try:
            await self._postgres_step(context)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # A defect, not a refusal: logged with its traceback and said once; the prompt goes on.
            _LOG.exception("the PostgreSQL step of the ACP bootstrap failed")
            self._postgres_settled = True
            await self._say(
                context.session_id,
                f"vibey could not check PostgreSQL: {type(exc).__name__}. The agent's log on "
                f"stderr has the details; `{INSTALL_COMMAND}` checks it in your own terminal.",
            )

    # -- steps 1 to 3 ----------------------------------------------------------------------

    async def _run_steps(self, session_id: str) -> None:
        try:
            doctor_ok = await self._doctor(session_id)
            connect_ok = await self._connect(session_id)
            services_ok = await self._services(session_id)
        finally:
            # Whatever happened, step 3 is over: a hub read may fall back to `vibey hub start`
            # unless the keep-alive now owns the hub's unit.
            if self._keep_alive is not None:
                self._keep_alive.handed_over()
        self._healthy = doctor_ok and connect_ok and services_ok

    async def _doctor(self, session_id: str) -> bool:
        checks = self._checks
        if checks is None:
            return True
        await self._notify(
            session_id, self._mapper.tool_call(TOOL_DOCTOR, "vibey doctor", ToolKind.READ, {})
        )
        shown: list[str] = []
        failed = False
        try:
            async with (
                self._step_timeout(self._settings.bootstrap_timeout_seconds),
                contextlib.aclosing(checks.each()) as each,
            ):
                async for _, results in each:
                    for result in results:
                        shown.append(self._finding(result))
                        failed = failed or result.mark == "FAIL"
                    await self._progress(session_id, TOOL_DOCTOR, shown)
        except TimeoutError:
            shown.append(self._overran("vibey doctor"))
            await self._end(session_id, TOOL_DOCTOR, ToolCallStatus.FAILED, shown)
            return False
        status = ToolCallStatus.FAILED if failed else ToolCallStatus.COMPLETED
        await self._end(session_id, TOOL_DOCTOR, status, shown or ["No checks ran."])
        return not failed

    async def _connect(self, session_id: str) -> bool:
        connector = self._connector
        if connector is None or not self._settings.auto_connect:
            return True
        if await asyncio.to_thread(connector.already_connected):
            return True
        await self._notify(
            session_id, self._mapper.tool_call(TOOL_CONNECT, "vibey connect", ToolKind.EDIT, {})
        )
        if self._machine.locked():
            await self._end(
                session_id,
                TOOL_CONNECT,
                ToolCallStatus.COMPLETED,
                [
                    "vibey is busy with its PostgreSQL step in this window, so it connects the "
                    "clients when the next session starts."
                ],
            )
            return False
        try:
            async with self._step_timeout(self._settings.bootstrap_timeout_seconds):
                held, problem = await self._enter_machine()
                if not held:
                    status = ToolCallStatus.FAILED if problem else ToolCallStatus.COMPLETED
                    why = (
                        f"vibey could not take its setup lock ({problem}); nothing was connected."
                        if problem
                        else "Another vibey acp on this computer is connecting the clients; "
                        "this one tries again when its next session starts."
                    )
                    await self._end(session_id, TOOL_CONNECT, status, [why])
                    return False
                results = await self._holding(connector.connect_detected())
        except TimeoutError:
            await self._end(
                session_id, TOOL_CONNECT, ToolCallStatus.FAILED, [self._overran("vibey connect")]
            )
            return False
        failed = any(result.mark in {"FAIL", "WARN"} for result in results)
        status = (
            ToolCallStatus.FAILED
            if any(result.mark == "FAIL" for result in results)
            else ToolCallStatus.COMPLETED
        )
        shown = [self._finding(result) for result in results]
        await self._end(session_id, TOOL_CONNECT, status, shown or ["No client to connect."])
        return not failed

    # -- step 3: the user-level services ----------------------------------------------------

    async def _services(self, session_id: str) -> bool:
        units, loader, hub = self._units, self._loader, self._hub
        names = self._settings.services
        if units is None or loader is None or hub is None:
            return True
        if not self._settings.auto_services or not names:
            return True
        await self._notify(
            session_id,
            self._mapper.tool_call(
                TOOL_SERVICES, "Keep vibey's services running", ToolKind.EXECUTE, {}
            ),
        )
        seconds = self._settings.bootstrap_timeout_seconds
        try:
            async with self._step_timeout(seconds), self._machine, self._lock.hold(seconds) as held:
                if not held:
                    await self._end(
                        session_id,
                        TOOL_SERVICES,
                        ToolCallStatus.FAILED,
                        [
                            "Another vibey acp on this computer held the setup lock past "
                            f"{seconds} s (`[acp] bootstrap_timeout_seconds`); this window loads "
                            "nothing now and tries again when its next session starts."
                        ],
                    )
                    return False
                return await self._load_services(session_id, units, loader, hub, names)
        except TimeoutError:
            await self._end(
                session_id,
                TOOL_SERVICES,
                ToolCallStatus.FAILED,
                [
                    f"{self._overran('Loading vibey services')} The hub may still be starting: "
                    "`vibey supervisor status` and the logs under `[supervisor] log_dir` say why."
                ],
            )
            return False

    async def _load_services(
        self,
        session_id: str,
        units: ServiceUnitsInterface,
        loader: ServiceLoaderInterface,
        hub: AcpHubPortInterface,
        names: tuple[str, ...],
    ) -> bool:
        refused = loader.refused()
        if refused:
            # As root: no unit, and no fallback hub either; said once in the tool call.
            await self._end(
                session_id, TOOL_SERVICES, ToolCallStatus.FAILED, [self._untrusted(refused)]
            )
            return False
        if not await asyncio.to_thread(loader.available):
            return await self._without_service_manager(session_id, units, loader)
        waiting: dict[str, str] = {}
        for name in names:
            reason = await asyncio.to_thread(units.waiting, name)
            if reason:
                waiting[name] = reason
        ready = tuple(name for name in names if name not in waiting)
        try:
            written = await asyncio.to_thread(units.write, ready, self._settings.restart)
        except Exception as exc:  # a cancel is a BaseException: it is never caught here
            # A refusal (ValueError) or a file that cannot be written (OSError): the tool call is
            # closed, never left spinning, and nothing is loaded.
            await self._end(
                session_id,
                TOOL_SERVICES,
                ToolCallStatus.FAILED,
                [f"No unit was written: {self._untrusted(f'{type(exc).__name__}: {exc}')}"],
            )
            return False
        shown = [
            f"{name}: not loaded yet: {self._untrusted(reason)}" for name, reason in waiting.items()
        ]
        managed: dict[str, str] = {}
        deferred: list[str] = []
        loaded: list[str] = []
        hub_label: str | None = None
        failed = False
        for name, outcome in zip(ready, written, strict=True):
            if name == HUB:
                hub_label = outcome.label
            said, kept = await self._load_one(name, outcome, loader, hub, deferred, loaded)
            shown.append(said)
            failed = failed or kept is None and outcome.action != "kept-differing"
            if kept is not None:
                managed[outcome.label] = kept
        # Handed over and said before the hub is waited for: a poll the step's bound cuts short
        # never leaves loaded units unmanaged or unsaid.
        if self._keep_alive is not None and managed:
            self._keep_alive.manage(managed, hub_label=hub_label, deferred=deferred)
        if loaded:
            await self._say_loaded(session_id, loader, loaded)
        if hub_label in managed:
            await self._hub_answers(hub)
        status = ToolCallStatus.FAILED if failed else ToolCallStatus.COMPLETED
        await self._end(session_id, TOOL_SERVICES, status, shown)
        # A service still waiting is tried again when the next session starts.
        return not failed and not waiting

    async def _load_one(
        self,
        name: str,
        written: UnitOutcome,
        loader: ServiceLoaderInterface,
        hub: AcpHubPortInterface,
        deferred: list[str],
        loaded: list[str],
    ) -> tuple[str, str | None]:
        """Load one written unit unless it runs already; what to show for it, and the unit
        file the keep-alive may manage (None: not vibey's to keep running)."""
        label = self._untrusted(written.label)
        if written.action == "kept-differing":
            return (
                f"{label}: {self._untrusted(written.path)} differs from what vibey renders, so "
                "it is kept as you edited it; vibey neither loads nor restarts it.",
                None,
            )
        if written.action not in WRITTEN:
            return f"{label}: the unit was not written: {self._untrusted(written.detail)}", None
        state = await asyncio.to_thread(loader.state, written.label)
        if state == "running":
            return f"{label}: already running.", written.path
        if name == HUB:
            pid = await asyncio.to_thread(self._units.detached_hub_pid) if self._units else None
            if pid is not None and await hub.healthy():
                deferred.append(written.label)
                return (
                    f"{label}: the hub is running outside the service manager (pid {pid}); "
                    "keep-alive takes it over when it exits.",
                    written.path,
                )
        outcome = await asyncio.to_thread(loader.load, written.label, written.path)
        if outcome.action == "failed":
            return f"{label}: could not be loaded: {self._untrusted(outcome.detail)}", None
        if outcome.action == "loaded":
            loaded.append(written.label)
            return f"{label}: loaded.", written.path
        return f"{label}: already loaded.", written.path

    async def _hub_answers(self, hub: AcpHubPortInterface) -> None:
        """Poll the hub until it answers; the step's own bound ends the wait."""
        while not await hub.healthy():
            await self._sleep(self._settings.live_poll_seconds)

    async def _without_service_manager(
        self, session_id: str, units: ServiceUnitsInterface, loader: ServiceLoaderInterface
    ) -> bool:
        """No service manager to load into: `vibey hub start` once per process, said."""
        domain = self._untrusted(loader.domain())
        if self._hub_started:
            await self._end(
                session_id,
                TOOL_SERVICES,
                ToolCallStatus.COMPLETED,
                [f"{domain} cannot be reached here, and vibey already started the hub once."],
            )
            return True
        self._hub_started = True
        worked = await asyncio.to_thread(units.start_hub)
        said = (
            f"{domain} cannot be reached on this computer (no login session's `gui` domain, or "
            "no `systemctl --user` manager), so vibey cannot keep its services running here. "
            + (
                "It started the hub once with `vibey hub start`; nothing restarts it if it stops."
                if worked
                else "It tried `vibey hub start` once, and that failed; run it yourself to see why."
            )
        )
        status = ToolCallStatus.COMPLETED if worked else ToolCallStatus.FAILED
        await self._end(session_id, TOOL_SERVICES, status, [said])
        await self._say(session_id, said)
        return worked

    async def _say_loaded(
        self, session_id: str, loader: ServiceLoaderInterface, loaded: list[str]
    ) -> None:
        labels = ", ".join(f"`{self._untrusted(label)}`" for label in loaded)
        commands = self._mapper.untrusted_code(
            "\n".join(loader.unload_commands(loaded)), limit=self._settings.live_message_chars
        )
        await self._say(
            session_id,
            f"vibey loaded these user-level services into {self._untrusted(loader.domain())}: "
            f"{labels}. The service manager restarts them when they stop, and they start again "
            f"when you log in. `{UNLOAD_COMMAND}` stops them for good: it unloads them and "
            "deletes the unit files vibey wrote (never one you edited). By hand, the same is:"
            f"\n\n{commands}\n\nSet `[acp] auto_services = false` in your own vibey.toml (in "
            "your configuration folder) so vibey does not load them again.",
        )

    async def _wait_for_steps(self, context: AcpSessionContext) -> None:
        steps = self._steps
        session_id = context.session_id
        if steps is None or steps.done() or session_id in self._waited:
            return
        self._waited.add(session_id)
        seconds = self._settings.bootstrap_timeout_seconds
        if not await self._wait(steps, seconds):
            await self._say(
                session_id,
                f"vibey's own setup (`vibey doctor`, `vibey connect`, its services) is still "
                f"running after "
                f"{seconds} s (`[acp] bootstrap_timeout_seconds`); this prompt goes ahead "
                "without it.",
            )

    # -- step 4: PostgreSQL ---------------------------------------------------------------

    async def _postgres_step(self, context: AcpSessionContext) -> None:
        postgres = self._postgres
        if (
            postgres is None
            or self._settings.install_postgres != "ask"
            or self._postgres_claimed
            or self._postgres_settled
        ):
            return
        if not self._may_run(context):
            # Observe triggers nothing privileged; it is told once, and a later prompt in a
            # mode that may run is still asked.
            if not self._observe_noted:
                self._observe_noted = True
                readiness = await self._checked(context, postgres)
                if readiness is not None and not readiness[0]:
                    await self._say(
                        context.session_id,
                        f"PostgreSQL is not ready ({readiness[1]}). This session observes, so "
                        "vibey does not offer to install it: switch to drive to be asked, or "
                        f"run `{INSTALL_COMMAND}` in your own terminal.",
                    )
            return
        self._postgres_claimed = True  # nothing awaited above: a second prompt finds it set
        try:
            await self._offer_postgres(context, postgres)
        finally:
            self._postgres_claimed = False

    async def _checked(
        self, context: AcpSessionContext, postgres: PostgresInstallerInterface
    ) -> tuple[bool, str, str | None] | None:
        """PostgreSQL's readiness, its detail (cleaned) and package manager, read off the loop
        within `bootstrap_timeout_seconds`; None, and said once, when the check overran."""
        seconds = self._settings.bootstrap_timeout_seconds
        try:
            async with self._step_timeout(seconds):
                readiness = await asyncio.to_thread(postgres.status)
        except TimeoutError:
            self._postgres_settled = True
            await self._say(
                context.session_id,
                f"vibey could not check PostgreSQL within {seconds} s "
                "(`[acp] bootstrap_timeout_seconds`), so it does not offer to install it in this "
                f"window; `{INSTALL_COMMAND}` checks and installs it from your own terminal.",
            )
            return None
        return readiness.ready, self._untrusted(readiness.detail), readiness.package_manager

    async def _offer_postgres(
        self, context: AcpSessionContext, postgres: PostgresInstallerInterface
    ) -> None:
        session_id = context.session_id
        readiness = await self._checked(context, postgres)
        if readiness is None:
            return
        ready, detail, manager = readiness
        if ready:
            self._postgres_settled = True
            return
        if manager is None or manager not in PACKAGE_MANAGERS:
            self._postgres_settled = True
            await self._say(
                session_id,
                f"PostgreSQL is not ready ({detail}), and vibey found no package manager it can "
                "install it with (brew, apt-get or dnf), so the hub runs degraded until it is "
                "installed.",
            )
            return
        try:
            async with self._step_timeout(self._settings.bootstrap_timeout_seconds):
                held, problem = await self._enter_machine()
        except TimeoutError:
            # This window's own connect step still holds the machine: not another process.
            await self._say(
                session_id,
                "vibey's own connect step is still running in this window, so it asks about "
                "PostgreSQL at your next prompt.",
            )
            return
        if not held:
            self._postgres_settled = True
            why = (
                f"vibey could not take its setup lock ({problem})"
                if problem is not None
                else "vibey's setup lock is held (by another vibey acp on this computer, or by "
                "this window's keep-alive while it brings the hub back)"
            )
            await self._say(
                session_id,
                f"PostgreSQL is not ready ({detail}), and {why}, so this window does not ask to "
                f"install it. `{INSTALL_COMMAND}` installs it from your own terminal.",
            )
            return
        try:
            await self._ask_and_install(context, postgres, manager, detail)
        finally:
            if not self._install_holds_machine:
                self._leave_machine()  # else the install's thread lets go when it ends

    async def _ask_and_install(
        self,
        context: AcpSessionContext,
        postgres: PostgresInstallerInterface,
        manager: str,
        detail: str,
    ) -> None:
        session_id = context.session_id
        asked = False
        try:
            await self._notify(
                session_id,
                self._mapper.tool_call(TOOL_POSTGRES, "Install PostgreSQL", ToolKind.EXECUTE, {}),
            )
            if context.state.cancel_requested:
                await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, [NOT_ASKED])
                return
            title = (
                f"Install PostgreSQL with {manager}? On Linux this needs sudo; if sudo asks for "
                f"a password, run `{INSTALL_COMMAND}` in your own terminal."
            )
            # Registered on the turn, so a `session/cancel` withdraws it at once and it resolves
            # as no answer: silence and a cancel are never consent.
            context.state.register_permission(TOOL_POSTGRES)
            self._postgres_settled = asked = True
            try:
                selected = await self._channel.request_permission(
                    session_id,
                    {"toolCallId": TOOL_POSTGRES, "title": title},
                    [dict(option) for option in POSTGRES_OPTIONS],
                    timeout=self._settings.permission_timeout_seconds,
                )
            finally:
                context.state.resolve_permission(TOOL_POSTGRES)
            if selected != INSTALL_OPTION or not self._may_run(context):
                await self._declined(session_id, detail)
                return
            await self._notify(
                session_id,
                self._mapper.tool_call_update(TOOL_POSTGRES, ToolCallStatus.IN_PROGRESS),
            )
            if not self._may_run(context) or context.state.cancel_requested:
                # A switch to observe, or a cancel, landed while the frame was written. Read with
                # nothing awaited between it and the install below.
                await self._declined(session_id, detail)
                return
        except asyncio.CancelledError:
            # Nothing was installed. The tool call is closed and, once asked, the degraded
            # message said, before the cancel goes on.
            if asked:
                await self._declined(session_id, detail)
            else:
                await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, [NOT_ASKED])
            raise
        try:
            outcome = await self._installing(session_id, postgres)
        except Exception as exc:
            await self._end(
                session_id,
                TOOL_POSTGRES,
                ToolCallStatus.FAILED,
                [f"The install broke: {type(exc).__name__}. The agent's log on stderr has why."],
            )
            raise
        said = self._untrusted(outcome.detail)
        if outcome.ok:
            await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.COMPLETED, [said])
            return
        if outcome.still_running:
            await self._end(
                session_id,
                TOOL_POSTGRES,
                ToolCallStatus.COMPLETED,
                [
                    f"An install command overran `[acp] install_timeout_seconds` and could not be "
                    f"stopped, so it may still be running ({said}). `vibey doctor` says when "
                    "PostgreSQL is ready."
                ],
            )
            return
        if outcome.needs_password:
            said = (
                "sudo needs a password, and vibey never asks for one or types one. Run "
                f"`{INSTALL_COMMAND}` in your own terminal. ({said})"
            )
        await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, [said])
        await self._say(session_id, self._degraded(said))

    async def _installing(
        self, session_id: str, postgres: PostgresInstallerInterface
    ) -> PostgresInstallOutcome:
        """Run the install on a thread that holds the machine until it has really ended: a
        cancel here stops the wait, never the install."""
        install = asyncio.ensure_future(asyncio.to_thread(postgres.install))
        self._install_holds_machine = True
        install.add_done_callback(lambda _: self._leave_machine())
        try:
            return await asyncio.shield(install)
        except asyncio.CancelledError:
            install.add_done_callback(lambda done: self._report_late(session_id, done))
            await self._end(
                session_id,
                TOOL_POSTGRES,
                ToolCallStatus.FAILED,
                [
                    "Cancelled here. The install you allowed goes on in the background; vibey "
                    "logs how it ends on stderr, and says so here if this window is still open."
                ],
            )
            raise

    def _report_late(
        self, session_id: str, install: asyncio.Future[PostgresInstallOutcome]
    ) -> None:
        if install.cancelled() or install.exception() is not None:
            _LOG.error(
                "the PostgreSQL install allowed over ACP failed", exc_info=install.exception()
            )
            said = "it failed; the agent's log on stderr has the details"
        else:
            outcome = install.result()
            _LOG.warning("the PostgreSQL install allowed over ACP ended: %s", outcome.detail)
            said = ("it finished: " if outcome.ok else "it did not finish: ") + self._untrusted(
                outcome.detail
            )
        if self._closed or session_id in self._gone:
            return
        task = asyncio.ensure_future(
            self._say(session_id, f"The PostgreSQL install you allowed has ended: {said}")
        )
        self._late.add(task)
        task.add_done_callback(self._late_said)

    def _late_said(self, task: asyncio.Task[None]) -> None:
        self._late.discard(task)
        self._reap(task)

    async def _declined(self, session_id: str, detail: str) -> None:
        await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, ["Not installed."])
        await self._say(session_id, self._degraded(detail))

    @staticmethod
    def _degraded(detail: str) -> str:
        return (
            f"PostgreSQL was not installed ({detail}), so the hub runs degraded until it is "
            f"ready: it cannot keep projects or their ledger. `{INSTALL_COMMAND}` installs it."
        )

    # -- the machine: in-process turns, and the lock file across processes ------------------

    async def _enter_machine(self) -> tuple[bool, str | None]:
        """Wait for this process's turn, then take the lock file. The lock file is taken with
        nothing awaited after the turn is granted, so no cancel can fall between taking it and
        the caller's `try` that lets it go."""
        await self._machine.acquire()
        try:
            taken = self._lock.acquire()
        except OSError as exc:
            self._machine.release()
            return False, self._untrusted(str(exc))
        if not taken:
            self._machine.release()
            return False, None
        return True, None

    def _leave_machine(self) -> None:
        self._lock.release()
        self._machine.release()

    async def _holding(self, work: Awaitable[tuple[DoctorResult, ...]]) -> tuple[DoctorResult, ...]:
        """Run a step that holds the machine; a cut-off step's thread lets go when it ends."""
        running = asyncio.ensure_future(work)
        try:
            results = await asyncio.shield(running)
        except BaseException:
            running.add_done_callback(lambda _: self._leave_machine())
            raise
        self._leave_machine()
        return results

    # -- helpers ----------------------------------------------------------------------------

    def _may_run(self, context: AcpSessionContext) -> bool:
        """Whether the session's mode may run anything at all (drive); observe may not. The
        install is no hub action, so the mode's own ceiling is asked, not the hub's grant."""
        try:
            return HubScope.RUN in self._modes.scopes_for(context.mode_id, frozenset(HubScope))
        except UnknownMode:
            return False

    def _finding(self, result: DoctorResult) -> str:
        said = f"{result.mark} {result.name}" + (f": {result.detail}" if result.detail else "")
        return self._untrusted(said)

    def _untrusted(self, text: str) -> str:
        return self._mapper.untrusted(text, limit=self._settings.live_message_chars)

    def _overran(self, what: str) -> str:
        return (
            f"{what} did not finish within {self._settings.bootstrap_timeout_seconds} s "
            "(`[acp] bootstrap_timeout_seconds`)."
        )

    async def _progress(self, session_id: str, tool_call_id: str, shown: list[str]) -> None:
        await self._notify(
            session_id,
            self._mapper.tool_call_update(
                tool_call_id, ToolCallStatus.IN_PROGRESS, self._joined(shown)
            ),
        )

    async def _end(
        self, session_id: str, tool_call_id: str, status: ToolCallStatus, shown: list[str]
    ) -> None:
        await self._notify(
            session_id, self._mapper.tool_call_update(tool_call_id, status, self._joined(shown))
        )

    @staticmethod
    def _joined(shown: list[str]) -> str:
        # Each finding is its own paragraph: one cleaned line each, never run together.
        return "\n\n".join(shown)

    async def _say(self, session_id: str, text: str) -> None:
        await self._notify(session_id, self._mapper.agent_text(text))

    async def _notify(self, session_id: str, update: Mapping[str, Any]) -> None:
        if self._closed or session_id in self._gone:
            return  # the connection or the session ended: nothing more is sent to it
        await self._channel.notify_update(session_id, update)

    @staticmethod
    async def _bounded_wait(task: asyncio.Task[None], seconds: float) -> bool:
        done, _ = await asyncio.wait({task}, timeout=seconds)
        return bool(done)

    @staticmethod
    def _reap(task: asyncio.Task[None]) -> None:
        # The outcome is read, so a failure (a client gone mid-update, a defect) is logged with
        # its traceback, never left "never retrieved".
        with contextlib.suppress(asyncio.CancelledError):
            error = task.exception()
            if error is not None:
                _LOG.error("the ACP bootstrap failed", exc_info=error)
