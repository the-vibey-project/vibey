# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One authority restarts the hub (ADR-0101, review M1/M2), composed as `vibey acp` wires it.

The real `AcpHubClient`, `HubGateway`, `HubStartRouter`, `BoundedHubStarter` and `AcpKeepAlive`,
over a fake hub process whose restart takes several polls to come up and a recording service
manager. Held here:

- probing the hub (`healthy`) never starts or restarts it;
- one probe of a dead hub restarts it once; two windows restart it once, the first holding the
  lock until the hub answers;
- step 3's first poll never restarts the hub it just loaded;
- a read that finds no hub while the keep-alive owns the unit only asks the keep-alive;
- an edited or deferred hub unit is never restarted: a read runs the `vibey hub start`
  fallback instead, and so does a process where no unit is managed.

Module-level test functions (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx
import pytest
from acp_fakes import FakeChannel, context

from vibey.application.acp.acp_bootstrap import TOOL_SERVICES, AcpBootstrap
from vibey.application.acp.acp_keep_alive import AcpKeepAlive
from vibey.application.acp.dto import UnitOutcome
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.errors import VibeyError
from vibey.infrastructure.acp.acp_hub_client import AcpHubClient
from vibey.infrastructure.acp.bootstrap_lock import BootstrapLock
from vibey.infrastructure.acp.hub_start_router import HubStartRouter
from vibey.infrastructure.mcp.hub_gateway import HubGateway
from vibey.infrastructure.mcp.hub_start_policy import BoundedHubStarter

HUB = "dev.vibey.hub"
WORKER = "dev.vibey.worker"
UNITS = {HUB: "/u/dev.vibey.hub.plist"}
SETTINGS = AcpSettings(probe_seconds=30, bootstrap_timeout_seconds=5, live_poll_seconds=0.2)


class HubProcess:
    """The hub as the network sees it: down, up, or starting (up after `polls` more reads)."""

    def __init__(self, *, up: bool) -> None:
        self.up = up
        self.starting = 0
        self.reads = 0
        self._guard = threading.Lock()

    def start(self, polls: int = 3) -> None:
        with self._guard:
            self.up = False
            self.starting = polls

    def answer(self) -> bool:
        with self._guard:
            self.reads += 1
            if self.starting:
                self.starting -= 1
                self.up = self.starting == 0
            return self.up


class Manager:
    """The service manager: a restart or load starts the hub, which takes three reads to answer."""

    def __init__(self, process: HubProcess) -> None:
        self.process = process
        self.calls: list[tuple[str, str]] = []
        self._guard = threading.Lock()

    def available(self) -> bool:
        return True

    def refused(self) -> str:
        return ""

    def state(self, label: str) -> str:
        return "running" if self.process.up or self.process.starting else "not loaded"

    def restart(self, label: str) -> UnitOutcome:
        with self._guard:
            self.calls.append(("restart", label))
        time.sleep(0.01)
        self.process.start()
        return UnitOutcome(label, UNITS.get(label, ""), "restarted")

    def load(self, label: str, unit: str) -> UnitOutcome:
        with self._guard:
            self.calls.append(("load", label))
        self.process.start()
        return UnitOutcome(label, unit, "loaded")

    def unload(self, label: str) -> UnitOutcome:
        raise AssertionError("never unloaded here")

    def forget_unit_files(self) -> UnitOutcome:
        raise AssertionError("never here")

    def unload_commands(self, labels: Iterable[str]) -> tuple[str, ...]:
        return ()

    def domain(self) -> str:
        return "launchd gui/501"


class Units:
    def __init__(self, *, pid: int | None = None) -> None:
        self.pid = pid

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        return tuple(UnitOutcome(HUB, UNITS[HUB], "created") for _ in names)

    def waiting(self, name: str) -> str:
        return ""

    def recorded(self) -> tuple[str, ...]:
        return ()

    def remove(self, label: str) -> UnitOutcome:
        raise AssertionError("never removed here")

    def label(self, name: str) -> str:
        return f"dev.vibey.{name}"

    def detached_hub_pid(self) -> int | None:
        return self.pid

    def start_hub(self) -> bool:
        raise AssertionError("no fallback start in these cases")


class Fallback:
    def __init__(self) -> None:
        self.starts = 0

    def __call__(self) -> bool:
        self.starts += 1
        return False


def _client_for(process: HubProcess) -> Any:
    class Client:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> Client:
            return self

        def __exit__(self, *exc: object) -> None:
            pass

        def request(self, method: str, route: str, **kwargs: Any) -> httpx.Response:
            if not process.answer():
                raise httpx.ConnectError("connection refused")
            return httpx.Response(200, text="{}")

    return Client


def _hub(tmp_path: Path, process: HubProcess, fallback: Fallback) -> tuple[AcpHubClient, Any]:
    state = tmp_path / "hub"
    state.mkdir(mode=0o700, exist_ok=True)
    (state / "serving.json").write_text(json.dumps({"host": "127.0.0.1", "port": 9, "pid": 1}))
    config = tmp_path / "vibey.toml"
    config.write_text(f'[hub]\nstate_dir = "{state}"\n')
    router = HubStartRouter(
        BoundedHubStarter(fallback, window_seconds=60, launch=lambda work: work())
    )
    gateway = HubGateway(config_path=lambda: config, starter=router, client=_client_for(process))
    return AcpHubClient(gateway=gateway), router


async def _yield(seconds: float) -> None:
    await asyncio.sleep(0)


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _keep_alive(
    tmp_path: Path, manager: Manager, hub: AcpHubClient, clock: Clock, units: Units | None = None
) -> AcpKeepAlive:
    return AcpKeepAlive(
        manager,
        hub,
        BootstrapLock(tmp_path / "lock", poll_seconds=0.005),
        FakeChannel(),
        AcpUpdateMapper(),
        SETTINGS,
        units=units or Units(),
        clock=clock,
        sleep=_yield,
    )


async def test_probing_the_hub_never_starts_or_restarts_it(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock)
    router.attach(kept)
    kept.manage(UNITS, hub_label=HUB, deferred=())

    assert [await hub.healthy() for _ in range(5)] == [False] * 5

    assert manager.calls == [] and fallback.starts == 0
    assert kept._current is None  # type: ignore[attr-defined]  # not even a probe asked for
    await kept.stop()


async def test_one_probe_of_a_dead_hub_restarts_it_once(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock)
    router.attach(kept)
    kept.manage(UNITS, hub_label=HUB, deferred=())
    clock.now += 31

    await kept.probe()

    assert manager.calls == [("restart", HUB)]
    assert fallback.starts == 0
    assert process.up  # the probe waited for it, inside the lock
    await kept.stop()


async def test_two_windows_restart_a_slow_hub_once(tmp_path: Path) -> None:
    process = HubProcess(up=False)
    manager, clock = Manager(process), Clock()
    windows = []
    for name in ("one", "two"):
        folder = tmp_path / name
        folder.mkdir()
        hub, router = _hub(folder, process, Fallback())
        kept = _keep_alive(tmp_path, manager, hub, clock)  # one lock folder for both
        router.attach(kept)
        kept.manage(UNITS, hub_label=HUB, deferred=())
        windows.append(kept)
    clock.now += 31

    # One probe each, at once, and no session timers: nothing else reads the hub meanwhile, so
    # only the first window's wait for the hub to answer keeps the second from restarting it.
    await asyncio.gather(*(window.probe() for window in windows))

    assert manager.calls == [("restart", HUB)]
    for window in windows:
        await window.stop()


async def test_a_read_that_finds_no_hub_only_asks_the_keep_alive(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock)
    router.attach(kept)
    kept.manage(UNITS, hub_label=HUB, deferred=())
    clock.now += 31

    for _ in range(3):  # three reads find no hub: one probe, one restart
        with pytest.raises(VibeyError, match="keep-alive"):
            await hub.chat("/projects", project_id=None, request_id="r")
    while kept._current is None:  # type: ignore[attr-defined]
        await asyncio.sleep(0)
    await asyncio.wait({kept._current})  # type: ignore[attr-defined]

    assert manager.calls == [("restart", HUB)]
    assert fallback.starts == 0
    await kept.stop()


async def test_step_three_never_restarts_the_hub_it_just_loaded(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    units = Units()
    kept = _keep_alive(tmp_path, manager, hub, clock, units)
    router.attach(kept)
    channel = FakeChannel()
    settings = AcpSettings(
        services=("hub",), bootstrap_timeout_seconds=5, live_poll_seconds=0.2, probe_seconds=30
    )
    boot = AcpBootstrap(
        settings,
        None,
        None,
        None,
        channel,
        AcpUpdateMapper(),
        BootstrapLock(tmp_path / "lock"),
        AcpModes(settings),
        units=units,
        loader=manager,
        hub=hub,
        keep_alive=kept,
        sleep=_yield,
    )

    boot.start("s")
    await asyncio.wait({boot._steps}, timeout=10)  # type: ignore[attr-defined, arg-type]
    await boot.before_first_prompt(context("s"))  # the first prompt's probe, too

    assert manager.calls == [("load", HUB)]
    assert fallback.starts == 0
    final = [u for u in channel.updates if u.get("toolCallId") == TOOL_SERVICES][-1]
    assert final["status"] == "completed"
    await boot.close()


async def test_a_deferred_hub_is_never_restarted_a_read_runs_the_fallback(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock, Units(pid=4242))
    router.attach(kept)
    kept.manage(UNITS, hub_label=HUB, deferred=(HUB,))
    clock.now += 31

    with pytest.raises(VibeyError):
        await hub.chat("/projects", project_id=None, request_id="r")
    await kept.probe()

    assert manager.calls == []  # neither restarted nor loaded beside the live detached hub
    assert fallback.starts == 1  # `vibey hub start`, which finds the running hub's lock held
    await kept.stop()


async def test_an_edited_hub_unit_is_never_restarted_a_read_runs_the_fallback(
    tmp_path: Path,
) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock)
    router.attach(kept)
    kept.manage({WORKER: "/u/w"}, hub_label=None, deferred=())  # the hub unit was edited

    with pytest.raises(VibeyError):
        await hub.chat("/projects", project_id=None, request_id="r")

    assert manager.calls == []
    assert fallback.starts == 1
    await kept.stop()


async def test_with_nothing_managed_a_read_runs_the_fallback(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    with pytest.raises(VibeyError):
        await hub.chat("/projects", project_id=None, request_id="r")
    assert fallback.starts == 1  # no keep-alive attached at all: today's `vibey hub start`


def test_the_router_is_its_interface() -> None:
    from vibey.infrastructure.acp.interfaces.hub_start_router_interface import (
        HubStartRouterInterface,
    )

    assert isinstance(HubStartRouter(Fallback()), HubStartRouterInterface)


async def test_a_fresh_machines_first_reads_start_no_hub_before_step_three_loads_the_unit(
    tmp_path: Path,
) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock, units = Manager(process), Clock(), Units()
    kept = _keep_alive(tmp_path, manager, hub, clock, units)
    router.attach(kept)

    # session/new's hub reads, while doctor and connect still run: no detached hub is started.
    for _ in range(3):
        with pytest.raises(VibeyError, match="setting up its service"):
            await hub.create_session("s", "/work")
    assert fallback.starts == 0 and manager.calls == []

    settings = AcpSettings(
        services=("hub",), bootstrap_timeout_seconds=5, live_poll_seconds=0.2, probe_seconds=30
    )
    boot = AcpBootstrap(
        settings,
        None,
        None,
        None,
        FakeChannel(),
        AcpUpdateMapper(),
        BootstrapLock(tmp_path / "lock"),
        AcpModes(settings),
        units=units,
        loader=manager,
        hub=hub,
        keep_alive=kept,
        sleep=_yield,
    )
    boot.start("s")
    await asyncio.wait({boot._steps}, timeout=10)  # type: ignore[attr-defined, arg-type]

    assert manager.calls == [("load", HUB)]  # step 3 loaded the unit; nothing raced it
    assert kept.owns_hub() and fallback.starts == 0
    await boot.close()


async def test_once_step_three_failed_a_read_falls_back_to_hub_start(tmp_path: Path) -> None:
    process, fallback = HubProcess(up=False), Fallback()
    hub, router = _hub(tmp_path, process, fallback)
    manager, clock = Manager(process), Clock()
    kept = _keep_alive(tmp_path, manager, hub, clock)
    router.attach(kept)
    kept.handed_over()  # step 3 ended without a unit for the hub

    with pytest.raises(VibeyError):
        await hub.create_session("s", "/work")
    assert fallback.starts == 1 and manager.calls == []
    await kept.stop()
    assert kept.awaiting_handover() is False
