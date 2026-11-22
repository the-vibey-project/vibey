# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpKeepAlive`: restart vibey's own units, once, under the lock, and say each change once.

The rules held here: only the labels vibey manages are restarted; a hub outside the service
manager is never stopped and is taken over only once its process has gone; a label is restarted
at most once per `probe_seconds`; two windows restart a dead hub once; and a crash loop is said
once per change of state, never once per probe. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import asyncio
import contextlib
import threading
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from acp_fakes import FakeChannel, FakeHub, context, until

from vibey.application.acp.acp_keep_alive import AcpKeepAlive
from vibey.application.acp.dto import UnitOutcome
from vibey.application.acp.interfaces.acp_keep_alive_interface import AcpKeepAliveInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.infrastructure.acp.bootstrap_lock import BootstrapLock

HUB = "dev.vibey.hub"
WORKER = "dev.vibey.worker"
UNITS = {HUB: "/u/dev.vibey.hub.plist", WORKER: "/u/dev.vibey.worker.plist"}


class Hub(FakeHub):
    def __init__(self, *, up: bool = True) -> None:
        super().__init__()
        self.up = up
        self.probes = 0

    async def healthy(self) -> bool:
        self.probes += 1
        await asyncio.sleep(0)  # a real hub read yields: let another window probe meanwhile
        return self.up


class Loader:
    def __init__(self, hub: Hub, *, running: set[str] | None = None) -> None:
        self.hub = hub
        self.running = set(running if running is not None else {WORKER})
        self.calls: list[tuple[str, str]] = []
        self.revives: set[str] = {HUB, WORKER}
        """The labels a restart or load brings back up."""
        self.fail: set[str] = set()
        self._guard = threading.Lock()

    def state(self, label: str) -> str:
        return "running" if label in self.running else "stopped (activating)"

    def restart(self, label: str) -> UnitOutcome:
        with self._guard:
            self.calls.append(("restart", label))
        time.sleep(0.02)  # the service manager takes a moment: another window may wait on it
        return self._done(label, "restarted")

    def load(self, label: str, unit: str) -> UnitOutcome:
        self.calls.append(("load", label))
        return self._done(label, "loaded")

    def _done(self, label: str, action: Any) -> UnitOutcome:
        if label in self.fail:
            return UnitOutcome(label, UNITS[label], "failed", "exited 5: <b>Input/output</b>")
        if label in self.revives:
            self.running.add(label)
            if label == HUB:
                self.hub.up = True
        return UnitOutcome(label, UNITS[label], action)


class FreeLock:
    def __init__(self, *, free: bool = True) -> None:
        self.free = free
        self.holds = 0

    def acquire(self) -> bool:
        return self.free

    def release(self) -> None:
        pass

    @contextlib.asynccontextmanager
    async def _held(self) -> AsyncIterator[bool]:
        self.holds += 1
        yield self.free

    def hold(self, timeout: float) -> Any:
        return self._held()


class Units:
    def __init__(self, pid: int | None = None) -> None:
        self.pid = pid

    def detached_hub_pid(self) -> int | None:
        return self.pid


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def keep_alive(
    hub: Hub,
    loader: Loader,
    channel: FakeChannel,
    *,
    lock: Any = None,
    clock: Clock | None = None,
    units: Units | None = None,
    settings: AcpSettings | None = None,
    sleep: Any = None,
) -> AcpKeepAlive:
    kept = AcpKeepAlive(
        loader,
        hub,
        lock if lock is not None else FreeLock(),
        channel,
        AcpUpdateMapper(),
        settings or AcpSettings(probe_seconds=30),
        units=units,
        clock=clock or Clock(),
        **({"sleep": sleep} if sleep is not None else {}),
    )
    return kept


def test_the_keep_alive_is_its_interface() -> None:
    hub = Hub()
    assert isinstance(keep_alive(hub, Loader(hub), FakeChannel()), AcpKeepAliveInterface)


async def test_nothing_managed_probes_nothing() -> None:
    hub = Hub(up=False)
    loader = Loader(hub)
    await keep_alive(hub, loader, FakeChannel()).probe(context())
    assert hub.probes == 0 and loader.calls == []


async def test_a_healthy_hub_and_running_worker_take_no_lock_and_say_nothing() -> None:
    hub, channel, lock = Hub(), FakeChannel(), FreeLock()
    loader = Loader(hub)
    kept = keep_alive(hub, loader, channel, lock=lock)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    await kept.probe(context())

    assert lock.holds == 0 and loader.calls == [] and channel.texts == []
    await kept.stop()


async def test_dead_hub_is_restarted_and_noticed_once() -> None:
    hub, channel, clock = Hub(up=False), FakeChannel(), Clock()
    loader = Loader(hub)
    loader.revives = set()  # it stays down: restarted, but never answers
    kept = keep_alive(hub, loader, channel, clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    for _ in range(4):
        clock.now += 31
        await kept.probe(context())

    assert loader.calls.count(("restart", HUB)) == 4
    restarted = [t for t in channel.texts if "restarted" in t]
    assert len(restarted) == 1 and HUB in restarted[0]

    hub.up = True
    clock.now += 31
    await kept.probe(context())
    clock.now += 31
    await kept.probe(context())
    assert [t for t in channel.texts if "running again" in t] == [f"`{HUB}` is running again."]
    await kept.stop()


async def test_a_label_is_restarted_at_most_once_per_probe_period() -> None:
    hub, clock = Hub(up=False), Clock()
    loader = Loader(hub)
    loader.revives = set()
    kept = keep_alive(hub, loader, FakeChannel(), clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    clock.now += 31
    for _ in range(10):  # ten prompts in a row
        await kept.probe(context())
        clock.now += 1

    assert loader.calls.count(("restart", HUB)) == 1
    await kept.stop()


async def test_a_unit_just_loaded_gets_a_probe_period_to_come_up() -> None:
    hub, clock = Hub(up=False), Clock()
    loader = Loader(hub)
    kept = keep_alive(hub, loader, FakeChannel(), clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    await kept.probe(context())
    assert loader.calls == []
    await kept.stop()


async def test_two_processes_serialise_bootstrap_and_restart_once(tmp_path: Path) -> None:
    # Two AcpKeepAlive instances sharing one BootstrapLock dir and one fake loader; after the
    # first restart the second's re-probe sees healthy and does nothing.
    hub = Hub(up=False)
    loader = Loader(hub)
    clock = Clock()
    windows = [
        keep_alive(
            hub,
            loader,
            FakeChannel(),
            lock=BootstrapLock(tmp_path, poll_seconds=0.005),
            clock=clock,
        )
        for _ in range(2)
    ]
    for window in windows:
        window.manage(UNITS, hub_label=HUB, deferred=())
    clock.now += 31

    await asyncio.gather(*(window.probe(context()) for window in windows))

    assert loader.calls.count(("restart", HUB)) == 1
    assert hub.probes >= 4  # both probed before and again under the lock
    for window in windows:
        await window.stop()


async def test_another_window_holding_the_lock_past_the_bound_means_no_restart_here() -> None:
    hub, clock = Hub(up=False), Clock()
    loader = Loader(hub)
    kept = keep_alive(hub, loader, FakeChannel(), lock=FreeLock(free=False), clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())
    clock.now += 31

    await kept.probe(context())

    assert loader.calls == []
    await kept.stop()


async def test_crash_looping_worker_notices_once_per_transition() -> None:
    hub, channel, clock = Hub(), FakeChannel(), Clock()
    loader = Loader(hub, running=set())
    loader.revives = set()  # the worker exits again at once
    kept = keep_alive(hub, loader, channel, clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    for _ in range(5):
        clock.now += 31
        await kept.probe(context())
    assert loader.calls.count(("restart", WORKER)) == 5
    assert len(channel.texts) == 1 and "restarted" in channel.texts[0]

    loader.fail = {WORKER}  # systemd gave up on it: the start limit was hit
    for _ in range(3):
        clock.now += 31
        await kept.probe(context())
    assert len(channel.texts) == 2
    assert "could not restart" in channel.texts[1]
    assert "<b>" not in channel.texts[1]  # the service manager's text is shown escaped

    loader.running.add(WORKER)
    for _ in range(3):
        clock.now += 31
        await kept.probe(context())
    assert len(channel.texts) == 3 and "running again" in channel.texts[2]
    await kept.stop()


async def test_a_label_vibey_does_not_manage_is_never_restarted() -> None:
    hub, clock = Hub(), Clock()
    loader = Loader(hub, running=set())
    kept = keep_alive(hub, loader, FakeChannel(), clock=clock)
    # The worker's unit was the operator's edit: vibey manages the hub alone.
    kept.manage({HUB: UNITS[HUB]}, hub_label=HUB, deferred=())
    clock.now += 31

    await kept.probe(context())

    assert loader.calls == []
    await kept.stop()


async def test_a_hub_outside_the_service_manager_is_never_stopped_only_taken_over() -> None:
    hub, channel, clock = Hub(up=False), FakeChannel(), Clock()
    loader = Loader(hub)
    units = Units(pid=4242)
    kept = keep_alive(hub, loader, channel, clock=clock, units=units)
    kept.manage(UNITS, hub_label=HUB, deferred=(HUB,))

    for _ in range(3):
        clock.now += 31
        await kept.probe(context())
    assert loader.calls == []  # neither restarted (which would race it) nor anything else
    assert len(channel.texts) == 1 and "pid 4242" in channel.texts[0]

    units.pid = None  # it exited
    clock.now += 31
    await kept.probe(context())
    assert loader.calls == [("load", HUB)]
    assert "loaded" in channel.texts[-1]

    hub.up = False  # now it is the unit's: a restart, not another load
    loader.revives = set()
    clock.now += 31
    await kept.probe(context())
    assert loader.calls[-1] == ("restart", HUB)
    await kept.stop()


async def test_a_take_over_that_fails_is_said_and_tried_again_next_period() -> None:
    hub, channel, clock = Hub(up=False), FakeChannel(), Clock()
    loader = Loader(hub)
    loader.fail = {HUB}
    kept = keep_alive(hub, loader, channel, clock=clock, units=Units(pid=None))
    kept.manage(UNITS, hub_label=HUB, deferred=(HUB,))

    clock.now += 31
    await kept.probe(context())
    await kept.probe(context())  # same period: not again
    clock.now += 31
    await kept.probe(context())

    assert loader.calls == [("load", HUB), ("load", HUB)]
    assert len(channel.texts) == 1 and "could not load" in channel.texts[0]
    await kept.stop()


async def test_without_a_way_to_ask_about_the_detached_hub_it_is_taken_over() -> None:
    hub, clock = Hub(up=False), Clock()
    loader = Loader(hub)
    kept = keep_alive(hub, loader, FakeChannel(), clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=(HUB,))
    clock.now += 31
    await kept.probe(context())
    assert loader.calls == [("load", HUB)]
    await kept.stop()


async def test_the_timer_probes_every_period_while_a_session_is_attached() -> None:
    hub = Hub(up=True)
    loader = Loader(hub)
    ticks: list[float] = []
    gate = asyncio.Event()

    async def sleep(seconds: float) -> None:
        ticks.append(seconds)
        if len(ticks) > 2:
            await gate.wait()

    kept = keep_alive(
        hub, loader, FakeChannel(), sleep=sleep, settings=AcpSettings(probe_seconds=7)
    )
    kept.manage(UNITS, hub_label=HUB, deferred=())
    assert ticks == []  # no session yet: no timer
    kept.attach("s")
    await until(lambda: len(ticks) >= 3)
    assert ticks[:3] == [7.0, 7.0, 7.0]
    assert hub.probes == 2

    kept.detach("s")
    await asyncio.sleep(0)
    assert kept._timer is None  # type: ignore[attr-defined]
    kept.attach("s")
    await kept.stop()
    kept.attach("s")
    assert kept._timer is None  # type: ignore[attr-defined]  # stopped: attaching restarts nothing
    kept.start()
    assert kept._timer is not None  # type: ignore[attr-defined]
    await kept.stop()


async def test_a_probe_that_breaks_is_logged_and_never_raises() -> None:
    class Broken(Hub):
        async def healthy(self) -> bool:
            raise RuntimeError("boom")

    hub = Broken()
    kept = keep_alive(hub, Loader(hub), FakeChannel())
    kept.manage(UNITS, hub_label=HUB, deferred=())
    await kept.probe(context())  # no exception
    await kept.stop()


async def test_a_probe_cancelled_is_cancelled_not_swallowed() -> None:
    class Hanging(Hub):
        async def healthy(self) -> bool:
            await asyncio.sleep(30)
            return True

    hub = Hanging()
    kept = keep_alive(hub, Loader(hub), FakeChannel())
    kept.manage(UNITS, hub_label=HUB, deferred=())
    task = asyncio.create_task(kept.probe(context()))
    await asyncio.sleep(0)
    task.cancel()
    results = await asyncio.gather(task, return_exceptions=True)
    assert isinstance(results[0], asyncio.CancelledError)
    await kept.stop()


async def test_every_attached_session_hears_a_change_and_a_detached_one_does_not() -> None:
    class Flaky(FakeChannel):
        async def notify_update(self, session_id: str, update: Any) -> None:
            if session_id == "gone":
                raise ConnectionResetError("the window closed")
            await super().notify_update(session_id, update)

    hub, channel, clock = Hub(up=False), Flaky(), Clock()
    loader = Loader(hub)
    loader.revives = set()
    kept = keep_alive(hub, loader, channel, clock=clock)
    kept.manage(UNITS, hub_label=HUB, deferred=())
    kept.attach("gone")
    kept.attach("a")
    kept.attach("b")
    kept.detach("b")
    clock.now += 31

    await kept.probe()

    assert channel.sessions == ["a"]
    await kept.stop()


async def test_detaching_an_unknown_session_and_stopping_twice_are_harmless() -> None:
    hub = Hub()
    kept = keep_alive(hub, Loader(hub), FakeChannel())
    kept.detach("never attached")
    await kept.stop()
    await kept.stop()
