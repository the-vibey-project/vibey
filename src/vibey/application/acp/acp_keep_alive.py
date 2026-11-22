# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps the hub and the worker `vibey acp` loaded running while an editor is connected (ADR-0101).

The service manager restarts a unit that exits (`[acp] restart`), throttled by
`[supervisor] restart_seconds` and, on systemd, a start limit. The keep-alive covers what it
cannot see: a hub process that is up but no longer answers, a unit systemd gave up on, a unit
someone stopped. It is the **one** authority that restarts a hub unit in this process: probing
the hub (`healthy`) has no side effect, and when a hub read finds no hub while the keep-alive
owns the hub's unit, the gateway asks for a probe (`request_probe`) instead of restarting
anything itself.

- **Only vibey's own units.** It restarts only the labels it was told it manages: the units
  vibey loaded, or found loaded as it renders them. An edited unit, a label it did not load, or
  a hub running outside the service manager is never restarted, and that hub is never stopped:
  its unit is loaded only once nothing holds the hub's lock any more.
- **Definitely down only.** A worker is down when the service manager says it is not loaded or
  failed. An unknown answer (a timeout), or a unit between states (`activating` during its
  restart wait, `reloading`), is not down: the service manager is already at it.
- **Probe, lock, probe again, wait.** When something is down it takes the bootstrap lock, the
  one per user, and probes again; only what is still down is restarted, and a restarted hub is
  waited for (within `bootstrap_timeout_seconds`) before the lock is let go. Two editor windows
  that both find the hub down therefore restart it once: the second finds it answering.
- **No hot loop.** A label is restarted at most once per `probe_seconds`, however many prompts
  arrive, and a unit just loaded or restarted gets that long to come up first.
- **Bounded at a prompt.** A prompt waits for the probe at most `prompt_probe_seconds`; the
  probe goes on to its end in the background. One probe runs at a time, shared by whoever asks.
- **Notices.** What the operator is told about a label is said when its state changes, twice at
  most within `notice_interval_seconds`; a unit that keeps stopping and starting is then
  reminded of at most once per that interval, never on every probe.

Every text from the service manager reaches the editor through `UntrustedTextInterface`.

Declared by `interfaces/acp_keep_alive_interface.py`.
"""

from __future__ import annotations

import asyncio
import logging
import math
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
DOWN_STATES: Final = frozenset({"not loaded", "stopped (failed)"})
"""What the service manager says of a unit that is definitely down; anything else -- running,
unknown, or between states -- is left to it."""
_LOG: Final = logging.getLogger(__name__)

type Sleep = Callable[[float], Awaitable[None]]


class AcpKeepAlive:
    """Declared by `interfaces/acp_keep_alive_interface.py::AcpKeepAliveInterface`.

    `units` answers whether a hub outside the service manager still holds its lock; `clock` and
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
        self._told: dict[str, list[float]] = {}
        """When each label's notices were said, for the interval that damps a flapping unit."""
        self._unsteady: set[str] = set()
        self._acted: dict[str, float] = {}
        """When each label was last loaded or restarted: at most once per `probe_seconds`."""
        self._current: asyncio.Task[None] | None = None
        """The one probe running now, shared by every prompt, the timer and a requested probe."""
        self._timer: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopped = False

    def manage(
        self, units: Mapping[str, str], *, hub_label: str | None, deferred: Iterable[str]
    ) -> None:
        self._loop = asyncio.get_running_loop()
        self._managed = dict(units)
        self._hub_label = hub_label if hub_label in self._managed else None
        self._deferred = {label for label in deferred if label in self._managed}
        now = self._clock()
        for label in self._managed:
            # Just loaded, or found running: give it a probe period to come up first.
            self._acted.setdefault(label, now)
        self._run_timer()

    def owns_hub(self) -> bool:
        return (
            not self._stopped
            and self._hub_label is not None
            and self._hub_label not in self._deferred
        )

    def request_probe(self) -> None:
        loop = self._loop
        if loop is None or self._stopped:
            return
        # From any thread (a hub read runs on one): the probe is started on the loop.
        loop.call_soon_threadsafe(self._shared)

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
        running = [task for task in (self._timer, self._current) if task is not None]
        self._timer = self._current = None
        for task in running:
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)

    async def probe(self, context: AcpSessionContext | None = None) -> None:
        if context is not None:
            self.attach(context.session_id)
        task = self._shared()
        if task is None:
            return
        # A prompt waits at most `prompt_probe_seconds`; the probe runs on without it.
        timeout = None if context is None else float(self._settings.prompt_probe_seconds)
        await asyncio.wait({task}, timeout=timeout)

    # -- the probe ---------------------------------------------------------------------------

    def _shared(self) -> asyncio.Task[None] | None:
        if not self._managed or self._stopped:
            return None
        if self._current is None or self._current.done():
            self._current = asyncio.get_running_loop().create_task(
                self._probe_guarded(), name="acp-keep-alive-probe"
            )
        return self._current

    async def _probe_guarded(self) -> None:
        try:
            await self._probe_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            # A defect or a client gone mid-notice: logged, and the prompt goes on.
            _LOG.exception("the ACP keep-alive probe failed")

    async def _probe_once(self) -> None:
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
            elif await asyncio.to_thread(self._loader.state, label) in DOWN_STATES:
                down.add(label)
        return down

    async def _settle(self, down: set[str]) -> None:
        """Every label not down is up: said once, if something else was said about it."""
        now = self._clock()
        for label in self._managed:
            if label in down:
                continue
            if self._said.get(label, UP) != UP:
                await self._tell(label, UP, f"{self._shown(label)} is running again.")
            self._said[label] = UP
            told = self._told.get(label, [])
            if label in self._unsteady and (not told or now - told[-1] >= self._interval):
                self._unsteady.discard(label)

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
        await self._answering(label)
        await self._tell(
            label,
            RESTARTED,
            f"{self._shown(label)} was down; vibey restarted it. If it keeps stopping, its log "
            "under `[supervisor] log_dir` says why.",
        )

    async def _answering(self, label: str) -> None:
        """Hold the lock until a restarted or loaded hub answers, or the bound passes, so a
        second window waiting on the lock finds it up rather than restarting it again."""
        if label != self._hub_label:
            return
        poll = self._settings.live_poll_seconds
        for _ in range(max(1, math.ceil(self._settings.bootstrap_timeout_seconds / poll))):
            if await self._hub.healthy():
                return
            await self._sleep(poll)

    async def _take_over(self, label: str, now: float) -> None:
        """A hub outside the service manager stopped answering. While it still holds the hub's
        lock it is left alone (never stopped); once nothing holds it, its unit is loaded."""
        pid = await asyncio.to_thread(self._units.detached_hub_pid) if self._units else None
        if pid is not None:
            held = f" (pid {pid})" if pid > 0 else ""
            await self._tell(
                label,
                OUTSIDE,
                f"The hub running outside the service manager{held} does not answer. vibey "
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
        await self._answering(label)
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

    @property
    def _interval(self) -> float:
        return float(self._settings.notice_interval_seconds)

    def _allowed(self, label: str, now: float) -> bool:
        """Two notices per label within the interval; past that the label is unsteady, and
        is reminded of at most once per interval."""
        recent = [t for t in self._told.get(label, []) if now - t < self._interval]
        if label in self._unsteady:
            return not recent
        if len(recent) >= 2:
            self._unsteady.add(label)
            return False
        return True

    async def _tell(self, label: str, state: str, text: str) -> None:
        if self._said.get(label) == state:
            return
        self._said[label] = state
        now = self._clock()
        if not self._allowed(label, now):
            return
        if label in self._unsteady:
            text = f"{self._shown(label)} keeps stopping and starting. Latest: {text}"
        self._told[label] = [*self._told.get(label, [])[-3:], now]
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
