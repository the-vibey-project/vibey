# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`BoundedHubStarter`: at most one `vibey hub start` per window, never in the caller's way.

`vibey acp` reads the hub from many places -- the live feed's polls, the journal's flushes, a
prompt's turn -- and every failed read reaches `HubGateway`'s start seam. Before, each one ran
`vibey hub start` (up to 15 s) where it stood. Now one attempt per `[acp] hub_start_seconds`
runs on a thread of its own, a failure is remembered until the window passes, and every caller
in between hears "the hub is away" at once. Also: B-7, the default starter's child never reads
the protocol's stdin, and B-8, the agent scopes are read again only when `vibey.toml` changes.
Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HubSettings
from vibey.infrastructure.mcp.hub_gateway import HubGateway, HubGatewayError, _default_starter
from vibey.infrastructure.mcp.hub_start_policy import BoundedHubStarter
from vibey.infrastructure.mcp.interfaces.hub_start_policy_interface import (
    BoundedHubStarterInterface,
)

CALL = HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects")


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Starter:
    def __init__(self, *outcomes: bool) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self) -> bool:
        self.calls += 1
        return self.outcomes.pop(0) if self.outcomes else False


def _inline(work: Callable[[], None]) -> None:
    work()


def _starter(starter: Starter, clock: Clock, *, window: float = 60) -> BoundedHubStarter:
    return BoundedHubStarter(starter, window_seconds=window, clock=clock, launch=_inline)


def test_one_start_per_window_and_every_caller_hears_the_hub_is_away() -> None:
    starter, clock = Starter(False), Clock()
    bounded = _starter(starter, clock)

    with pytest.raises(HubGatewayError, match="the hub is away"):
        bounded()
    for _ in range(5):  # the feed's polls, the journal's flushes: none starts it again
        clock.now += 10
        with pytest.raises(HubGatewayError, match="the hub is away"):
            bounded()

    assert starter.calls == 1


def test_a_failed_start_is_remembered_until_the_window_passes() -> None:
    starter, clock = Starter(False, True), Clock()
    bounded = _starter(starter, clock, window=30)

    with pytest.raises(HubGatewayError):
        bounded()
    clock.now += 29
    with pytest.raises(HubGatewayError, match="`vibey hub start` failed"):
        bounded()
    assert starter.calls == 1
    clock.now += 2
    with pytest.raises(HubGatewayError, match="starting it"):
        bounded()

    assert starter.calls == 2


def test_a_start_that_worked_is_not_repeated_within_the_window() -> None:
    starter, clock = Starter(True), Clock()
    bounded = _starter(starter, clock)

    with pytest.raises(HubGatewayError):
        bounded()
    clock.now += 5
    with pytest.raises(HubGatewayError, match="the hub is away"):
        bounded()

    assert starter.calls == 1


def test_the_start_runs_off_the_callers_thread_and_never_blocks_it() -> None:
    release, entered = threading.Event(), threading.Event()
    seen: list[str] = []

    def slow() -> bool:
        seen.append(threading.current_thread().name)
        entered.set()
        release.wait(10)
        return True

    bounded = BoundedHubStarter(slow, window_seconds=60)
    with pytest.raises(HubGatewayError, match="starting it"):
        bounded()  # returns at once: the start has not finished
    assert entered.wait(5)
    with pytest.raises(HubGatewayError, match="still starting"):
        bounded()  # a second caller while it runs neither waits nor starts another
    release.set()
    bounded.join(5)

    assert seen and seen[0] != threading.current_thread().name


def test_a_starter_that_raises_counts_as_a_failed_start() -> None:
    clock = Clock()

    def broken() -> bool:
        raise OSError("no python")

    bounded = BoundedHubStarter(broken, window_seconds=60, clock=clock, launch=_inline)
    with pytest.raises(HubGatewayError):
        bounded()
    with pytest.raises(HubGatewayError, match="failed"):
        bounded()


def test_the_gateway_reports_the_hub_away_at_once_through_the_bounded_starter(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    toml = tmp_path / "vibey.toml"
    toml.write_text(f"[hub]\nstate_dir = '{state}'\n")
    starter, clock = Starter(False), Clock()
    gateway = HubGateway(config_path=lambda: toml, starter=_starter(starter, clock))

    for _ in range(3):  # no hub was ever started: no serving record
        with pytest.raises(HubGatewayError, match="the hub is away"):
            gateway.call(CALL)
    LocalTokenStore(state).record_serving(ServingRecord(host="127.0.0.1", port=1, pid=1, tls=False))

    def refused(**kwargs: Any) -> Any:
        raise httpx.ConnectError("refused")

    down = HubGateway(config_path=lambda: toml, client=refused, starter=_starter(starter, clock))
    with pytest.raises(HubGatewayError, match="the hub is away"):
        down.call(CALL)
    assert starter.calls == 2  # one per bounded starter, never one per read


def test_the_bounded_starter_satisfies_its_interface() -> None:
    assert isinstance(BoundedHubStarter(Starter(), window_seconds=1), BoundedHubStarterInterface)


# -- B-7: the default starter's child never touches the protocol streams -----------------


def test_the_default_starter_runs_with_stdin_closed_and_output_captured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def run(argv: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", run)

    assert _default_starter() is True
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["capture_output"] is True


# -- B-8: the agent scopes are read again only when vibey.toml changes -------------------


class _CountingSettings:
    def __init__(self) -> None:
        self.loads = 0

    def load(self, path: Path) -> HubSettings:
        self.loads += 1
        return HubSettings(agent_scopes=frozenset({HubScope.VIEW}))


def test_the_agent_scopes_are_read_again_only_when_the_file_changes(tmp_path: Path) -> None:
    toml = tmp_path / "vibey.toml"
    toml.write_text("[hub]\n")
    settings = _CountingSettings()
    gateway = HubGateway(settings=settings, config_path=lambda: toml)

    for _ in range(5):
        assert gateway.agent_scopes() == frozenset({HubScope.VIEW})
    assert settings.loads == 1

    toml.write_text("[hub]\nagent_scopes = ['view']\n")
    gateway.agent_scopes()
    assert settings.loads == 2
    toml.unlink()
    gateway.agent_scopes()
    gateway.agent_scopes()
    assert settings.loads == 3


def test_a_start_that_cannot_launch_is_not_left_running() -> None:
    clock = Clock()

    def no_threads(work: Callable[[], None]) -> None:
        raise RuntimeError("can't start new thread")

    bounded = BoundedHubStarter(Starter(True), window_seconds=60, clock=clock, launch=no_threads)

    with pytest.raises(HubGatewayError, match="could not start it"):
        bounded()
    with pytest.raises(HubGatewayError, match="failed"):  # not "still starting it" for ever
        bounded()
    bounded.join(1)


def test_a_file_swapped_in_by_rename_is_read_again(tmp_path: Path) -> None:
    toml = tmp_path / "vibey.toml"
    toml.write_text("[hub]\n")
    settings = _CountingSettings()
    gateway = HubGateway(settings=settings, config_path=lambda: toml)
    gateway.agent_scopes()
    stat = toml.stat()
    other = tmp_path / "other.toml"
    other.write_text("[hub]\n")  # the same size
    os.utime(other, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # and the same mtime
    other.replace(toml)

    gateway.agent_scopes()

    assert settings.loads == 2
