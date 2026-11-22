# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bootstrap's SearXNG step: offer once to install the local SearXNG search asks first
(ADR-0102). It runs inside a prompt turn, after the PostgreSQL step, at most once per process.

**When it asks.** Only with `[acp] searxng = "ask"` and `auto_services` on (it loads a unit), in a
session whose mode may run things (never in observe), and only when none of these holds: the
person's environment names their own SearXNG (`VIBEY_SEARXNG_URL`), a SearXNG already passes the
identity check, vibey installed one before (step 3 then keeps its unit running), or the person
stopped it for good (`vibey acp unload`, `vibey searxng uninstall`). With no container runtime it
says once how to get one, and nothing else; with something not vibey's SearXNG already listening
on the port, it says so and asks nothing (a unit there would only fail at every login).

**What it asks.** `session/request_permission`, titled with the image's digest, the port and what
it costs: "Install SearXNG" (allow once) or "Not now" (reject once). Only that one option id, in a
session that may still run things when the answer comes back, installs. A cancel, a timeout, a
reject, any other option id, a switch to observe: nothing is installed, and search goes on asking
the local SearXNG first and Brave only as a backup.

**What it does on allow,** each part reported in the tool call: the image is pulled and the
settings and provision record written (`SearxngProvisionerInterface.prepare`, bounded by
`install_timeout_seconds`); the unit `<label_prefix>.searxng` is written like the hub's (never
over an edited one) and loaded into the person's own service manager, handed to the keep-alive
and said with the commands that unload it; then the step waits, within
`bootstrap_timeout_seconds`, until the SearXNG answers as vibey's own. A failure says one cleaned
reason. A cancel during an install that was allowed does not stop it: it is said, and the
machine is held until it has ended.

**Who else could install.** Inside the bootstrap's machine turn (its in-process lock and the
cross-process `acp-bootstrap.lock`): a second window finds the lock held and asks nothing, and one
that waited finds the SearXNG already provisioned and asks nothing either.

Every text from a runtime or a service manager reaches the editor through
`UntrustedTextInterface`. Declared by `interfaces/acp_searxng_step_interface.py`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from typing import Any, Final

from vibey.application.acp.dto import AcpSessionContext, SearxngOffer, UnitOutcome
from vibey.application.acp.interfaces.acp_keep_alive_interface import AcpKeepAliveInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.application.acp.interfaces.searxng_provisioner_interface import (
    SearxngProvisionerInterface,
)
from vibey.application.acp.interfaces.service_loader_interface import ServiceLoaderInterface
from vibey.application.acp.interfaces.service_units_interface import ServiceUnitsInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.modes import UnknownMode
from vibey.domain.acp.protocol import PermissionKind, ToolCallStatus, ToolKind
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_scope import HubScope
from vibey.domain.supervisor import SEARXNG

TOOL_SEARXNG: Final = "bootstrap-searxng"
INSTALL_OPTION: Final = "bootstrap-searxng:install"
NOT_NOW_OPTION: Final = "bootstrap-searxng:not-now"
INSTALL_COMMAND: Final = "vibey searxng install"
"""What the person runs in their own terminal to install it without an editor."""
UNLOAD_COMMAND: Final = "vibey acp unload"
SEARXNG_OPTIONS: Final[tuple[Mapping[str, str], ...]] = (
    {
        "optionId": INSTALL_OPTION,
        "name": "Install SearXNG",
        "kind": PermissionKind.ALLOW_ONCE.value,
    },
    {"optionId": NOT_NOW_OPTION, "name": "Not now", "kind": PermissionKind.REJECT_ONCE.value},
)
WRITTEN: Final = frozenset({"created", "unchanged", "updated"})
NOT_ASKED: Final = "Not asked: the prompt was cancelled first. vibey asks at your next prompt."
BACKUP: Final = (
    "Search goes on asking a local SearXNG first, and Brave only as a backup when a key is set."
)
NO_RUNTIME: Final = (
    "vibey searches a local SearXNG first, and runs it in a container, but found neither podman "
    "nor docker on your PATH. Install Podman (https://podman.io) or Docker, then run "
    f"`{INSTALL_COMMAND}`. vibey never installs a container runtime itself. {BACKUP}"
)
_LOG: Final = logging.getLogger(__name__)

type StepTimeout = Callable[[float], AbstractAsyncContextManager[Any]]
type Sleep = Callable[[float], Awaitable[None]]
type Enter = Callable[[], Awaitable[tuple[bool, str | None]]]
type Leave = Callable[[], None]
type Notify = Callable[[str, Mapping[str, Any]], Awaitable[None]]


class AcpSearxngStep:
    """Declared by `interfaces/acp_searxng_step_interface.py::AcpSearxngStepInterface`.

    `step_timeout` and `sleep` are the clock seams (`asyncio.timeout`, `asyncio.sleep`)."""

    def __init__(
        self,
        settings: AcpSettings,
        provisioner: SearxngProvisionerInterface,
        units: ServiceUnitsInterface,
        loader: ServiceLoaderInterface,
        channel: ClientChannelInterface,
        mapper: AcpUpdateMapperInterface,
        modes: AcpModesInterface,
        *,
        keep_alive: AcpKeepAliveInterface | None = None,
        step_timeout: StepTimeout | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._provisioner = provisioner
        self._units = units
        self._loader = loader
        self._channel = channel
        self._mapper = mapper
        self._modes = modes
        self._keep_alive = keep_alive
        self._step_timeout: StepTimeout = step_timeout or asyncio.timeout
        self._sleep = sleep
        self._claimed = False
        """Set, with nothing awaited before it, by the one prompt running the step now."""
        self._settled = False
        """The step is done for this process: asked, or nothing to ask."""
        self._late: set[asyncio.Future[Any]] = set()
        self._handed = False
        """The machine was handed to an allowed install, which lets it go when it has ended."""

    @property
    def pending(self) -> bool:
        return self._allowed() and not self._settled

    def wanted(self) -> bool:
        return (
            self._allowed() and self._provisioner.provisioned() and not self._provisioner.disabled()
        )

    def held_back(self) -> str:
        if (
            self._settings.auto_services
            and self._settings.searxng == "never"
            and self._provisioner.provisioned()
            and not self._provisioner.disabled()
        ):
            return (
                'vibey\'s SearXNG is installed, but `[acp] searxng = "never"`, so vibey neither '
                "loads nor restarts its unit here. The service manager still starts it at login: "
                "`vibey searxng uninstall` (or `vibey acp unload`) stops it for good."
            )
        return ""

    async def close(self) -> None:
        running = list(self._late)
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)

    async def offer(
        self, context: AcpSessionContext, *, enter: Enter, leave: Leave, notify: Notify
    ) -> None:
        if not self._allowed() or self._claimed or self._settled or not self._may_run(context):
            return  # observe asks nothing; a later prompt in drive still may be asked
        self._claimed = True  # nothing awaited above: a second prompt finds it set
        try:
            await self._offer(context, enter, leave, notify)
        finally:
            self._claimed = False

    # -- asking ----------------------------------------------------------------------------

    def _allowed(self) -> bool:
        return self._settings.auto_services and self._settings.searxng == "ask"

    async def _offer(
        self, context: AcpSessionContext, enter: Enter, leave: Leave, notify: Notify
    ) -> None:
        session_id = context.session_id
        found = await self._look(session_id, notify)
        if found is None or self._nothing_to_ask(found):
            return
        if found.runtime is None:
            self._settled = True
            await self._say(notify, session_id, NO_RUNTIME)
            return
        busy = await asyncio.to_thread(self._provisioner.busy)
        if busy:
            self._settled = True  # an occupied port would leave a unit failing at every login
            await self._say(notify, session_id, f"{self._untrusted(busy)}. {BACKUP}")
            return
        try:
            async with self._step_timeout(self._settings.bootstrap_timeout_seconds):
                held, problem = await enter()
        except TimeoutError:
            # This window's own earlier step still holds the machine: asked at the next prompt.
            await self._say(
                notify,
                session_id,
                "vibey's own setup is still busy in this window, so it offers SearXNG at your "
                "next prompt.",
            )
            return
        if not held:
            self._settled = True
            why = f" ({problem})" if problem else ""
            await self._say(
                notify,
                session_id,
                f"vibey's setup lock is held{why}, so this window does not offer to install "
                f"SearXNG; `{INSTALL_COMMAND}` installs it from your own terminal. {BACKUP}",
            )
            return
        self._handed = False
        try:
            again = await self._look(session_id, notify)  # another window may have installed it
            if again is None or self._nothing_to_ask(again):
                return
            await self._ask_and_install(context, again, leave, notify)
        finally:
            if not self._handed:
                leave()

    async def _look(self, session_id: str, notify: Notify) -> SearxngOffer | None:
        seconds = self._settings.bootstrap_timeout_seconds
        try:
            async with self._step_timeout(seconds):
                return await asyncio.to_thread(self._provisioner.offer)
        except TimeoutError:
            self._settled = True
            await self._say(
                notify,
                session_id,
                f"vibey could not check its local SearXNG within {seconds} s "
                f"(`[acp] bootstrap_timeout_seconds`), so it does not offer to install it in this "
                f"window; `{INSTALL_COMMAND}` does from your own terminal. {BACKUP}",
            )
            return None

    def _nothing_to_ask(self, found: SearxngOffer) -> bool:
        if found.own_url or found.answering or found.provisioned or found.disabled:
            # Theirs, already answering, kept running by step 3, or stopped for good by the
            # person: `vibey searxng install` is the one way back from that.
            self._settled = True
            return True
        return False

    async def _ask_and_install(
        self, context: AcpSessionContext, found: SearxngOffer, leave: Leave, notify: Notify
    ) -> None:
        """Ask, then install on allow. Once the machine is handed to the install (`_handed`),
        the install lets it go when it has really ended, a cancel or not."""
        session_id = context.session_id
        asked = False
        try:
            await notify(
                session_id,
                self._mapper.tool_call(TOOL_SEARXNG, "Install SearXNG", ToolKind.EXECUTE, {}),
            )
            if context.state.cancel_requested:
                await self._end(notify, session_id, ToolCallStatus.FAILED, [NOT_ASKED])
                return
            title = (
                f"Download and run SearXNG (searxng/searxng@sha256:{self._untrusted(found.short)}) "
                f"in a container on 127.0.0.1:{found.port}? vibey searches it first; this "
                f"downloads its container image with {self._untrusted(found.runtime or '')} and "
                "keeps a container running."
            )
            # Registered on the turn, so a `session/cancel` withdraws it at once and it resolves
            # as no answer: silence and a cancel are never consent.
            context.state.register_permission(TOOL_SEARXNG)
            self._settled = asked = True
            try:
                selected = await self._channel.request_permission(
                    session_id,
                    {"toolCallId": TOOL_SEARXNG, "title": title},
                    [dict(option) for option in SEARXNG_OPTIONS],
                    timeout=self._settings.permission_timeout_seconds,
                )
            finally:
                context.state.resolve_permission(TOOL_SEARXNG)
            if selected != INSTALL_OPTION or not self._may_run(context):
                await self._declined(notify, session_id)
                return
            await notify(
                session_id,
                self._mapper.tool_call_update(TOOL_SEARXNG, ToolCallStatus.IN_PROGRESS),
            )
            if not self._may_run(context) or context.state.cancel_requested:
                await self._declined(notify, session_id)
                return
        except asyncio.CancelledError:
            if asked:
                await self._declined(notify, session_id)
            else:
                await self._end(notify, session_id, ToolCallStatus.FAILED, [NOT_ASKED])
            raise
        install = asyncio.ensure_future(self._install(session_id, found, notify))
        install.add_done_callback(lambda _: leave())
        self._handed = True  # nothing awaited since the callback: a cancel cannot fall between
        try:
            ok, shown = await asyncio.shield(install)
        except asyncio.CancelledError:
            install.add_done_callback(lambda done: self._report_late(session_id, done, notify))
            await self._end(
                notify,
                session_id,
                ToolCallStatus.FAILED,
                [
                    "Cancelled here. The install you allowed goes on in the background; vibey "
                    "logs how it ends on stderr, and says so here if this window is still open."
                ],
            )
            raise
        except Exception as exc:
            _LOG.exception("the SearXNG install allowed over ACP broke")
            await self._end(
                notify,
                session_id,
                ToolCallStatus.FAILED,
                [f"The install broke: {type(exc).__name__}. The agent's log on stderr has why."],
            )
            await self._say(notify, session_id, BACKUP)
            return
        status = ToolCallStatus.COMPLETED if ok else ToolCallStatus.FAILED
        await self._end(notify, session_id, status, shown)
        if not ok:
            await self._say(notify, session_id, f"SearXNG was not set up: {shown[-1]} {BACKUP}")

    # -- installing --------------------------------------------------------------------------

    async def _install(
        self, session_id: str, found: SearxngOffer, notify: Notify
    ) -> tuple[bool, list[str]]:
        """Pull and write, write and load the unit, then wait for it to answer as vibey's own."""
        prepared = await asyncio.to_thread(self._provisioner.prepare)
        detail = self._untrusted(prepared.detail)
        if not prepared.ok:
            if prepared.still_running:
                detail += (
                    " It may still be running; `vibey doctor` says when the image is here, and "
                    f"`{INSTALL_COMMAND}` finishes the install."
                )
            return False, [f"Not installed: {detail}"]
        shown = [detail]
        try:
            (unit,) = await asyncio.to_thread(self._units.write, (SEARXNG,), self._settings.restart)
        except Exception as exc:  # a cancel is a BaseException: it is never caught here
            return False, [
                *shown,
                f"No unit was written: {self._untrusted(f'{type(exc).__name__}: {exc}')}",
            ]
        failure = await self._load(session_id, unit, notify)
        if failure is not None:
            return False, [*shown, failure]
        if await self._answers():
            return True, [
                *shown,
                f"SearXNG answers as vibey's own on 127.0.0.1:{found.port}; search asks it first.",
            ]
        return False, [
            *shown,
            f"{self._untrusted(unit.label)} is loaded, but SearXNG did not answer as vibey's own "
            f"within {self._settings.bootstrap_timeout_seconds} s; `vibey doctor` says when it "
            "does, and its log under `[supervisor] log_dir` says why it does not.",
        ]

    async def _load(self, session_id: str, unit: UnitOutcome, notify: Notify) -> str | None:
        """Load the written unit, unless it runs already; why not, or None."""
        label = self._untrusted(unit.label)
        if unit.action == "kept-differing":
            return (
                f"{label}: {self._untrusted(unit.path)} differs from what vibey renders, so it is "
                "kept as you edited it; vibey neither loads nor restarts it."
            )
        if unit.action not in WRITTEN:
            return f"{label}: the unit was not written: {self._untrusted(unit.detail)}"
        refused = self._loader.refused()
        if refused:
            return self._untrusted(refused)
        if not await asyncio.to_thread(self._loader.available):
            return (
                f"{self._untrusted(self._loader.domain())} cannot be reached here, so nothing "
                "keeps SearXNG running; run `vibey searxng serve` yourself to start it."
            )
        if await asyncio.to_thread(self._loader.state, unit.label) != "running":
            loaded = await asyncio.to_thread(self._loader.load, unit.label, unit.path)
            if loaded.action == "failed":
                return f"{label}: could not be loaded: {self._untrusted(loaded.detail)}"
            if loaded.action == "loaded":
                await self._say_loaded(notify, session_id, unit.label)
        if self._keep_alive is not None:
            self._keep_alive.add({unit.label: unit.path})
        return None

    async def _answers(self) -> bool:
        """Poll the identity check until vibey's SearXNG answers, within the bound."""
        try:
            async with self._step_timeout(self._settings.bootstrap_timeout_seconds):
                while not await asyncio.to_thread(self._provisioner.answering):
                    await self._sleep(self._settings.live_poll_seconds)
        except TimeoutError:
            return False
        return True

    async def _say_loaded(self, notify: Notify, session_id: str, label: str) -> None:
        commands = self._mapper.untrusted_code(
            "\n".join(self._loader.unload_commands([label])),
            limit=self._settings.live_message_chars,
        )
        await self._say(
            notify,
            session_id,
            f"vibey loaded `{self._untrusted(label)}` into "
            f"{self._untrusted(self._loader.domain())}: it runs SearXNG in a container on "
            "127.0.0.1 and starts again when you log in. "
            f"`{UNLOAD_COMMAND}` stops it for good (it removes the container and marks it so no "
            "session loads it again until `vibey searxng install`); by hand, the unit alone is:"
            f'\n\n{commands}\n\nSet `[acp] searxng = "never"` in your own vibey.toml so vibey '
            "does not offer it again.",
        )

    def _report_late(
        self,
        session_id: str,
        install: asyncio.Future[tuple[bool, list[str]]],
        notify: Notify,
    ) -> None:
        error = None if install.cancelled() else install.exception()
        if install.cancelled() or error is not None:
            _LOG.error("the SearXNG install allowed over ACP failed", exc_info=error)
            said = "it failed; the agent's log on stderr has the details"
        else:
            ok, shown = install.result()
            _LOG.warning("the SearXNG install allowed over ACP ended: %s", shown[-1])
            said = ("it finished: " if ok else "it did not finish: ") + shown[-1]
        task = asyncio.ensure_future(
            self._say(notify, session_id, f"The SearXNG install you allowed has ended: {said}")
        )
        self._late.add(task)
        task.add_done_callback(self._late.discard)

    # -- helpers -----------------------------------------------------------------------------

    async def _declined(self, notify: Notify, session_id: str) -> None:
        await self._end(notify, session_id, ToolCallStatus.FAILED, ["Not installed."])
        await self._say(
            notify,
            session_id,
            f"SearXNG was not installed. `{INSTALL_COMMAND}` installs it from your own terminal; "
            f'`[acp] searxng = "never"` stops vibey offering. {BACKUP}',
        )

    def _may_run(self, context: AcpSessionContext) -> bool:
        try:
            return HubScope.RUN in self._modes.scopes_for(context.mode_id, frozenset(HubScope))
        except UnknownMode:
            return False

    def _untrusted(self, text: str) -> str:
        return self._mapper.untrusted(text, limit=self._settings.live_message_chars)

    async def _end(
        self, notify: Notify, session_id: str, status: ToolCallStatus, shown: list[str]
    ) -> None:
        await notify(
            session_id, self._mapper.tool_call_update(TOOL_SEARXNG, status, "\n\n".join(shown))
        )

    async def _say(self, notify: Notify, session_id: str, text: str) -> None:
        await notify(session_id, self._mapper.agent_text(text))
