# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey acp` sets up on its own when an editor first connects (SP-ACP, steps 1, 2 and 4).

`[acp] auto_bootstrap` is the operator's grant for this; with it off nothing here runs.

1. **Doctor** (`tool_call` "vibey doctor", `read`): the local doctor's checks, one
   `tool_call_update` per finished check carrying every result so far (a client replaces a tool
   call's content), then `completed`, or `failed` when a check found `FAIL`.
2. **Connect** (`tool_call` "vibey connect", `edit`), when `[acp] auto_connect` is on and this
   vibey version has not connected yet: `vibey mcp` is registered with the user-scope clients
   installed here, never a project file and never a folder it would have to make.
3. **Services** -- loading and keeping the hub and the worker running -- is SP-ACP Task 8's.
4. **PostgreSQL**, only inside a prompt turn and only when `[acp] install_postgres = "ask"`: when
   it is not ready, the client is asked with `session/request_permission`, and only the
   "Install PostgreSQL" option installs. "Not now", a timeout, a cancel, any other option id
   and a session that observes install nothing. The install runs `PostgresLocalService`'s fixed
   argv with `sudo -n`, so it never waits at a password prompt; a sudo that wants one is told
   to the operator with the command to run themselves.

Steps 1 to 3 run as one task started after `session/new` has answered, so a slow check never
delays the answer; the first prompt of each session waits for that task within
`[acp] bootstrap_timeout_seconds` and then goes ahead regardless. They never run twice at once,
never again once a run finished healthy, and run again only when a new session starts after an
unhealthy run -- never in a loop. Step 4 runs once per process. Steps 2 and 4 change the
computer, so they also hold `<state_dir>/acp-bootstrap.lock`: a second editor window leaves
them to the first. Every text from a check, the connector or the installer is the machine's,
not vibey's: it reaches the client through `UntrustedTextInterface`, one cut line per finding.

Declared by `interfaces/acp_bootstrap_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, Final

from vibey.application.acp.dto import AcpSessionContext, DoctorResult
from vibey.application.acp.interfaces.bootstrap_lock_interface import BootstrapLockInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.application.acp.interfaces.doctor_checks_interface import DoctorChecksInterface
from vibey.application.acp.interfaces.host_connector_interface import HostConnectorInterface
from vibey.application.acp.interfaces.postgres_installer_interface import (
    PostgresInstallerInterface,
)
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.modes import UnknownMode
from vibey.domain.acp.protocol import PermissionKind, ToolCallStatus, ToolKind
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_scope import HubScope

TOOL_DOCTOR: Final = "bootstrap-doctor"
TOOL_CONNECT: Final = "bootstrap-connect"
TOOL_POSTGRES: Final = "bootstrap-postgres"
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
_LOG: Final = logging.getLogger(__name__)

type StepWait = Callable[[asyncio.Task[None], float], Awaitable[bool]]
"""Wait for the background steps up to a number of seconds; True when they finished."""
type StepTimeout = Callable[[float], AbstractAsyncContextManager[Any]]
"""The bound one step runs under (`asyncio.timeout`); it raises `TimeoutError` when it ends."""


class AcpBootstrap:
    """Declared by `interfaces/acp_bootstrap_interface.py::AcpBootstrapInterface`.

    `checks`, `connector` and `postgres` are each optional: a step with nothing to run says
    nothing. `wait` and `step_timeout` are the clock seams (`asyncio.wait`, `asyncio.timeout`).
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
        wait: StepWait | None = None,
        step_timeout: StepTimeout | None = None,
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
        self._steps: asyncio.Task[None] | None = None
        self._healthy = False
        self._waited: set[str] = set()
        """The sessions whose first prompt already waited for the background steps."""
        self._postgres_claimed = False
        """Set, with nothing awaited before it, by the one prompt that runs step 4."""
        self._postgres_settled = False
        self._observe_noted = False

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
        if not self._settings.auto_bootstrap or self._healthy:
            return
        if self._steps is not None and not self._steps.done():
            return
        # A task of its own: the caller (session/new) answers before the task first runs, and
        # the peer writes that answer before any update the task sends.
        self._steps = asyncio.create_task(
            self._run_steps(session_id), name=f"acp-bootstrap-{session_id}"
        )
        self._steps.add_done_callback(self._reap)

    async def before_first_prompt(self, context: AcpSessionContext) -> None:
        if not self._settings.auto_bootstrap:
            return
        await self._wait_for_steps(context)
        try:
            await self._postgres_step(context)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # A defect, not a refusal: logged with its traceback and said once; the prompt goes on.
            _LOG.exception("the PostgreSQL step of the ACP bootstrap failed")
            await self._say(
                context.session_id,
                f"vibey could not check PostgreSQL: {type(exc).__name__}. The agent's log on "
                f"stderr has the details; `{INSTALL_COMMAND}` checks it in your own terminal.",
            )

    # -- steps 1 to 3 ----------------------------------------------------------------------

    async def _run_steps(self, session_id: str) -> None:
        doctor_ok = await self._doctor(session_id)
        connect_ok = await self._connect(session_id)
        # Step 3 (load and keep the user-level services running) is SP-ACP Task 8's.
        self._healthy = doctor_ok and connect_ok

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
        held, problem = await self._take_lock()
        if problem is not None:
            await self._end(
                session_id,
                TOOL_CONNECT,
                ToolCallStatus.FAILED,
                [f"vibey could not take its setup lock ({problem}); nothing was connected."],
            )
            return False
        if not held:
            await self._end(
                session_id,
                TOOL_CONNECT,
                ToolCallStatus.COMPLETED,
                [
                    "Another vibey acp on this computer is connecting the clients; this one leaves it to that one."
                ],
            )
            return True
        try:
            async with self._step_timeout(self._settings.bootstrap_timeout_seconds):
                results = await connector.connect_detected()
        except TimeoutError:
            await self._end(
                session_id, TOOL_CONNECT, ToolCallStatus.FAILED, [self._overran("vibey connect")]
            )
            return False
        finally:
            await asyncio.to_thread(self._lock.release)
        failed = any(result.mark == "FAIL" for result in results)
        status = ToolCallStatus.FAILED if failed else ToolCallStatus.COMPLETED
        shown = [self._finding(result) for result in results]
        await self._end(session_id, TOOL_CONNECT, status, shown or ["No client to connect."])
        return not failed

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
                f"vibey's own setup (`vibey doctor`, `vibey connect`) is still running after "
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
                readiness = await asyncio.to_thread(postgres.status)
                if not readiness.ready:
                    await self._say(
                        context.session_id,
                        f"PostgreSQL is not ready ({self._untrusted(readiness.detail)}). This "
                        "session observes, so vibey does not offer to install it: switch to "
                        f"drive to be asked, or run `{INSTALL_COMMAND}` in your own terminal.",
                    )
            return
        self._postgres_claimed = True  # nothing awaited above: a second prompt finds it set
        try:
            await self._offer_postgres(context, postgres)
        finally:
            self._postgres_settled = True

    async def _offer_postgres(
        self, context: AcpSessionContext, postgres: PostgresInstallerInterface
    ) -> None:
        session_id = context.session_id
        readiness = await asyncio.to_thread(postgres.status)
        if readiness.ready:
            return
        detail = self._untrusted(readiness.detail)
        manager = readiness.package_manager
        if manager is None or manager not in PACKAGE_MANAGERS:
            await self._say(
                session_id,
                f"PostgreSQL is not ready ({detail}), and vibey found no package manager it can "
                "install it with (brew, apt-get or dnf), so the hub runs degraded until it is "
                "installed.",
            )
            return
        held, problem = await self._take_lock()
        if not held:
            why = (
                f"vibey could not take its setup lock ({problem})"
                if problem is not None
                else "another vibey acp on this computer is setting it up"
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
            await asyncio.to_thread(self._lock.release)

    async def _ask_and_install(
        self,
        context: AcpSessionContext,
        postgres: PostgresInstallerInterface,
        manager: str,
        detail: str,
    ) -> None:
        session_id = context.session_id
        await self._notify(
            session_id,
            self._mapper.tool_call(TOOL_POSTGRES, "Install PostgreSQL", ToolKind.EXECUTE, {}),
        )
        if context.state.cancel_requested:
            await self._declined(session_id, detail)
            return
        title = (
            f"Install PostgreSQL with {manager}? On Linux this needs sudo; if sudo asks for a "
            f"password, run `{INSTALL_COMMAND}` in your own terminal."
        )
        # Registered on the turn, so a `session/cancel` withdraws it at once and it resolves as
        # no answer: silence and a cancel are never consent.
        context.state.register_permission(TOOL_POSTGRES)
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
            session_id, self._mapper.tool_call_update(TOOL_POSTGRES, ToolCallStatus.IN_PROGRESS)
        )
        if not self._may_run(context) or context.state.cancel_requested:
            # A switch to observe, or a cancel, landed while the frame was written. Read with
            # nothing awaited between it and the install below.
            await self._declined(session_id, detail)
            return
        outcome = await asyncio.to_thread(postgres.install)
        said = self._untrusted(outcome.detail)
        if outcome.ok:
            await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.COMPLETED, [said])
            return
        if outcome.needs_password:
            said = (
                "sudo needs a password, and vibey never asks for one or types one. Run "
                f"`{INSTALL_COMMAND}` in your own terminal. ({said})"
            )
        await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, [said])
        await self._say(session_id, self._degraded(said))

    async def _declined(self, session_id: str, detail: str) -> None:
        await self._end(session_id, TOOL_POSTGRES, ToolCallStatus.FAILED, ["Not installed."])
        await self._say(session_id, self._degraded(detail))

    @staticmethod
    def _degraded(detail: str) -> str:
        return (
            f"PostgreSQL was not installed ({detail}), so the hub runs degraded until it is "
            f"ready: it cannot keep projects or their ledger. `{INSTALL_COMMAND}` installs it."
        )

    # -- helpers ----------------------------------------------------------------------------

    def _may_run(self, context: AcpSessionContext) -> bool:
        """Whether the session's mode may run anything at all (drive); observe may not. The
        install is no hub action, so the mode's own ceiling is asked, not the hub's grant."""
        try:
            return HubScope.RUN in self._modes.scopes_for(context.mode_id, frozenset(HubScope))
        except UnknownMode:
            return False

    async def _take_lock(self) -> tuple[bool, str | None]:
        try:
            return await asyncio.to_thread(self._lock.acquire), None
        except OSError as exc:
            return False, self._untrusted(str(exc))

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
        await self._channel.notify_update(session_id, update)

    @staticmethod
    async def _bounded_wait(task: asyncio.Task[None], seconds: float) -> bool:
        done, _ = await asyncio.wait({task}, timeout=seconds)
        return bool(done)

    @staticmethod
    def _reap(task: asyncio.Task[None]) -> None:
        # The steps' outcome is read, so a failure (a client gone mid-update, a defect) is
        # logged with its traceback, never left "never retrieved".
        with contextlib.suppress(asyncio.CancelledError):
            error = task.exception()
            if error is not None:
                _LOG.error("the ACP bootstrap failed", exc_info=error)
