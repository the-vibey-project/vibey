# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps the hub and the worker `vibey acp` loaded running while an editor is connected (ADR-0101).

The service manager restarts a unit that exits (`[acp] restart`), throttled by
`[supervisor] restart_seconds` and, on systemd, a start limit. The keep-alive covers what it
cannot see: a hub process that is up but no longer answers, a unit systemd gave up on, a unit
someone stopped. It probes at the start of every prompt and every `[acp] probe_seconds` while a
session is attached:

- **Only vibey's own units.** It restarts only the labels it was told it manages: the units
  vibey loaded, or found loaded exactly as it renders them. An edited unit, a label it did not
  load, or a hub running outside the service manager is never restarted, and that hub is never
  stopped: its unit is loaded only once its process has gone.
- **Probe, lock, probe again.** When something is down it takes the bootstrap lock, the one per
  user, and probes again; only what is still down is restarted. Two editor windows that both
  find the hub down therefore restart it once: the second finds it up when its turn comes.
- **No hot loop.** A label is restarted at most once per `probe_seconds`, however many prompts
  arrive; a crash loop is the service manager's throttle's to slow and the operator's to see.
- **One notice per change.** What the operator is told about a label is said when its state
  changes (down and restarted, restart failed, running again), never on every probe.

Every text from the service manager reaches the editor through `UntrustedTextInterface`.

Declared by `interfaces/acp_keep_alive_interface.py`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Final

from vibey.application.acp.dto import AcpSessionContext
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.bootstrap_lock_interface import BootstrapLockInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.application.acp.interfaces.service_loader_interface import ServiceLoaderInterface
from vibey.application.acp.interfaces.service_units_interface import ServiceUnitsInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.settings import AcpSettings

UP: Final = "up"
RESTARTED: Final = "restarted"
FAILED: Final = "failed"
OUTSIDE: Final = "outside"
TAKEN_OVER: Final = "taken-over"
_LOG: Final = logging.getLogger(__name__)

type Sleep = Callable[[float], Awaitable[None]]


class AcpKeepAlive:
    """Declared by `interfaces/acp_keep_alive_interface.py::AcpKeepAliveInterface`.

    `units` answers whether a hub outside the service manager is still alive; `clock` and
    `sleep` are the time seams."""

    def __init__(
        self,
        loader: ServiceLoaderInterface,
        hub: AcpHubPortInterface,
        lock: BootstrapLockInterface,
        channel: ClientChannelInterface,
        mapper: AcpUpdateMapperInterface,
        settings: AcpSettings,
        *,
        units: ServiceUnitsInterface | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._loader = loader
        self._hub = hub
        self._lock = lock
        self._channel = channel
        self._mapper = mapper
        self._settings = settings
        self._units = units
        self._clock = clock
        self._sleep = sleep
        self._managed: dict[str, str] = {}
        self._hub_label: str | None = None
        self._deferred: set[str] = set()
        self._sessions: list[str] = []
        self._said: dict[str, str] = {}
        """The state last said for each label: one notice per change, never per probe."""
        self._acted: dict[str, float] = {}
        """When each label was last loaded or restarted: at most once per `probe_seconds`."""
        self._probing = asyncio.Lock()
        self._timer: asyncio.Task[None] | None = None
        self._stopped = False

    def manage(
        self, units: Mapping[str, str], *, hub_label: str | None, deferred: Iterable[str]
    ) -> None:
        self._managed = dict(units)
        self._hub_label = hub_label if hub_label in self._managed else None
        self._deferred = {label for label in deferred if label in self._managed}
        now = self._clock()
        for label in self._managed:
            # Just loaded, or found running: give it a probe period to come up first.
            self._acted.setdefault(label, now)
        self._run_timer()

    def attach(self, session_id: str) -> None:
        if session_id not in self._sessions:
            self._sessions.append(session_id)
        self._run_timer()

    def detach(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions.remove(session_id)
        if not self._sessions and self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def start(self) -> None:
        self._stopped = False
        self._run_timer()

    async def stop(self) -> None:
        self._stopped = True
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()
            await asyncio.gather(timer, return_exceptions=True)

    async def probe(self, context: AcpSessionContext | None = None) -> None:
        if context is not None:
            self.attach(context.session_id)
        if not self._managed or self._stopped:
            return
        try:
            async with self._probing:
                await self._probe_held()
        except asyncio.CancelledError:
            raise
        except Exception:
            # A defect or a client gone mid-notice: logged, and the prompt goes on.
            _LOG.exception("the ACP keep-alive probe failed")

    # -- the probe ---------------------------------------------------------------------------

    async def _probe_held(self) -> None:
        if not await self._down():
            await self._settle(set())
            return
        async with self._lock.hold(float(self._settings.probe_seconds)) as held:
            if not held:
                return  # another vibey acp holds it: that window is probing and restarting
            down = await self._down()  # again, now that no other window can be restarting
            await self._settle(down)
            for label in down:
                await self._revive(label)

    async def _down(self) -> set[str]:
        down: set[str] = set()
        for label in self._managed:
            if label == self._hub_label:
                if not await self._hub.healthy():
                    down.add(label)
            elif await asyncio.to_thread(self._loader.state, label) != "running":
                down.add(label)
        return down

    async def _settle(self, down: set[str]) -> None:
        """Every label not down is up: said once, if something else was said about it."""
        for label in self._managed:
            if label in down:
                continue
            if self._said.get(label, UP) != UP:
                await self._tell(label, UP, f"{self._shown(label)} is running again.")
            self._said[label] = UP

    async def _revive(self, label: str) -> None:
        now = self._clock()
        if label in self._deferred:
            await self._take_over(label, now)
            return
        if now - self._acted.get(label, float("-inf")) < self._settings.probe_seconds:
            return
        self._acted[label] = now
        outcome = await asyncio.to_thread(self._loader.restart, label)
        if outcome.action == "failed":
            await self._tell(
                label,
                FAILED,
                f"{self._shown(label)} is down and vibey could not restart it: "
                f"{self._untrusted(outcome.detail)}. Its log under `[supervisor] log_dir` says "
                "why it stopped.",
            )
            return
        await self._tell(
            label,
            RESTARTED,
            f"{self._shown(label)} was down; vibey restarted it. If it keeps stopping, its log "
            "under `[supervisor] log_dir` says why.",
        )

    async def _take_over(self, label: str, now: float) -> None:
        """A hub outside the service manager stopped answering. While its process lives it is
        left alone (never stopped); once it has gone, its unit is loaded."""
        pid = await asyncio.to_thread(self._units.detached_hub_pid) if self._units else None
        if pid is not None:
            await self._tell(
                label,
                OUTSIDE,
                f"The hub running outside the service manager (pid {pid}) does not answer. vibey "
                "does not stop a process it did not start; when it exits, keep-alive loads "
                f"{self._shown(label)} in its place.",
            )
            return
        if now - self._acted.get(label, float("-inf")) < self._settings.probe_seconds:
            return
        self._acted[label] = now
        outcome = await asyncio.to_thread(self._loader.load, label, self._managed[label])
        if outcome.action == "failed":
            await self._tell(
                label,
                FAILED,
                f"The hub outside the service manager has gone, and vibey could not load "
                f"{self._shown(label)} in its place: {self._untrusted(outcome.detail)}.",
            )
            return
        self._deferred.discard(label)
        await self._tell(
            label,
            TAKEN_OVER,
            f"The hub outside the service manager has gone; vibey loaded {self._shown(label)} "
            "in its place, so the service manager keeps it running from now on.",
        )

    # -- the timer -----------------------------------------------------------------------------

    def _run_timer(self) -> None:
        if self._stopped or not self._managed or not self._sessions:
            return
        if self._timer is not None and not self._timer.done():
            return
        self._timer = asyncio.get_running_loop().create_task(self._tick(), name="acp-keep-alive")

    async def _tick(self) -> None:
        while True:
            await self._sleep(float(self._settings.probe_seconds))
            await self.probe()

    # -- saying it -----------------------------------------------------------------------------

    async def _tell(self, label: str, state: str, text: str) -> None:
        if self._said.get(label) == state:
            return
        self._said[label] = state
        update = self._mapper.agent_text(text)
        for session_id in list(self._sessions):
            try:
                await self._channel.notify_update(session_id, update)
            except Exception:  # a cancel is a BaseException: it is never caught here
                # One window gone mid-notice never keeps the others from hearing it.
                _LOG.warning("the keep-alive could not tell session %s", session_id, exc_info=True)

    def _shown(self, label: str) -> str:
        return f"`{self._untrusted(label)}`"

    def _untrusted(self, text: str) -> str:
        return self._mapper.untrusted(text, limit=self._settings.live_message_chars)
