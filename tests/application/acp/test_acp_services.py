# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpBootstrap` step 3: load and keep the user-level hub and worker units (ADR-0101).

Held here: nothing runs with `[acp] auto_services = false`; a label already running is left
alone; a hub running outside the service manager is not loaded over (nor stopped); an edited
unit is neither loaded nor kept alive; the first load says each label and the exact unload
commands; with no service manager, `vibey hub start` runs once per process and that is said;
and every machine text reaches the editor escaped. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Iterable, Mapping
from typing import Any

from acp_fakes import FakeChannel, FakeHub, context

from vibey.application.acp.acp_bootstrap import TOOL_SERVICES, AcpBootstrap
from vibey.application.acp.dto import AcpSessionContext, UnitOutcome
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper

HUB = "dev.vibey.hub"
WORKER = "dev.vibey.worker"
PATHS = {
    HUB: "/home/op/Library/LaunchAgents/dev.vibey.hub.plist",
    WORKER: "/home/op/Library/LaunchAgents/dev.vibey.worker.plist",
}
LABELS = {"hub": HUB, "worker": WORKER}


class Units:
    def __init__(self, *, actions: Mapping[str, str] | None = None, pid: int | None = None) -> None:
        self.actions = dict(actions or {})
        self.pid = pid
        self.writes: list[tuple[tuple[str, ...], str]] = []
        self.started = 0
        self.start_works = True
        self.error: Exception | None = None
        self.waits: dict[str, str] = {}

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        self.writes.append((names, restart))
        if self.error is not None:
            raise self.error
        return tuple(
            UnitOutcome(
                LABELS[name],
                PATHS[LABELS[name]],
                self.actions.get(name, "created"),  # type: ignore[arg-type]
                "<i>disk full</i>" if self.actions.get(name) == "failed" else "",
            )
            for name in names
        )

    def detached_hub_pid(self) -> int | None:
        return self.pid

    def waiting(self, name: str) -> str:
        return self.waits.get(name, "")

    def recorded(self) -> tuple[str, ...]:
        return ()

    def remove(self, label: str) -> UnitOutcome:
        return UnitOutcome(label, "", "absent")

    def label(self, name: str) -> str:
        return LABELS[name]

    def start_hub(self) -> bool:
        self.started += 1
        return self.start_works


class Loader:
    def __init__(self, *, running: set[str] | None = None, available: bool = True) -> None:
        self.running = set(running or ())
        self.is_available = available
        self.calls: list[tuple[str, str]] = []
        self.fail: set[str] = set()
        self.already: set[str] = set()
        self.refusal = ""

    def available(self) -> bool:
        return self.is_available

    def refused(self) -> str:
        return self.refusal

    def state(self, label: str) -> str:
        return "running" if label in self.running else "not loaded"

    def load(self, label: str, unit: str) -> UnitOutcome:
        self.calls.append(("load", label))
        assert unit == PATHS[label]
        if label in self.fail:
            return UnitOutcome(label, unit, "failed", "`bootstrap` exited 5: <b>EIO</b>")
        if label in self.already:
            return UnitOutcome(label, unit, "already-loaded")
        self.running.add(label)
        return UnitOutcome(label, unit, "loaded")

    def restart(self, label: str) -> UnitOutcome:
        self.calls.append(("restart", label))
        return UnitOutcome(label, PATHS[label], "restarted")

    def unload_commands(self, labels: Iterable[str]) -> tuple[str, ...]:
        return tuple(f"launchctl bootout gui/501/{label}" for label in labels)

    def domain(self) -> str:
        return "launchd gui/501"


class Hub(FakeHub):
    def __init__(self, *, up: bool = True, after: int = 0) -> None:
        super().__init__()
        self.up = up
        self.after = after
        self.probes = 0

    async def healthy(self) -> bool:
        self.probes += 1
        return self.up or self.probes > self.after > 0


class KeepAlive:
    def __init__(self) -> None:
        self.managed: list[tuple[dict[str, str], str | None, list[str]]] = []
        self.attached: list[str] = []
        self.detached: list[str] = []
        self.probes: list[str] = []
        self.stopped = False

    def manage(
        self, units: Mapping[str, str], *, hub_label: str | None, deferred: Iterable[str]
    ) -> None:
        self.managed.append((dict(units), hub_label, list(deferred)))

    def attach(self, session_id: str) -> None:
        self.attached.append(session_id)

    def detach(self, session_id: str) -> None:
        self.detached.append(session_id)

    async def probe(self, context: AcpSessionContext | None = None) -> None:
        assert context is not None
        self.probes.append(context.session_id)

    def start(self) -> None:
        pass

    async def stop(self) -> None:
        self.stopped = True


class Lock:
    def __init__(self, *, free: bool = True) -> None:
        self.free = free
        self.holds: list[float] = []

    def acquire(self) -> bool:
        return True

    def release(self) -> None:
        pass

    @contextlib.asynccontextmanager
    async def _held(self) -> AsyncIterator[bool]:
        yield self.free

    def hold(self, timeout: float) -> Any:
        self.holds.append(timeout)
        return self._held()


async def _no_sleep(seconds: float) -> None:
    await asyncio.sleep(0)


def bootstrap(
    channel: FakeChannel,
    *,
    settings: AcpSettings | None = None,
    units: Units | None = None,
    loader: Loader | None = None,
    hub: Hub | None = None,
    keep_alive: KeepAlive | None = None,
    lock: Lock | None = None,
    **seams: Any,
) -> AcpBootstrap:
    chosen = settings or AcpSettings()
    return AcpBootstrap(
        chosen,
        None,
        None,
        None,
        channel,
        AcpUpdateMapper(),
        lock or Lock(),
        AcpModes(chosen),
        units=units if units is not None else Units(),
        loader=loader if loader is not None else Loader(),
        hub=hub if hub is not None else Hub(),
        keep_alive=keep_alive,
        sleep=seams.pop("sleep", _no_sleep),
        **seams,
    )


async def run(boot: AcpBootstrap, session_id: str = "s") -> None:
    boot.start(session_id)
    steps = boot._steps  # type: ignore[attr-defined]
    if steps is not None:
        await asyncio.wait({steps}, timeout=5)
    assert boot.steps_finished


def services_updates(channel: FakeChannel) -> list[dict[str, Any]]:
    return [u for u in channel.updates if u.get("toolCallId") == TOOL_SERVICES]


def final(channel: FakeChannel) -> dict[str, Any]:
    return services_updates(channel)[-1]


async def test_auto_services_false_runs_nothing() -> None:
    channel, units, loader = FakeChannel(), Units(), Loader()
    boot = bootstrap(channel, settings=AcpSettings(auto_services=False), units=units, loader=loader)
    await run(boot)

    assert units.writes == [] and loader.calls == [] and services_updates(channel) == []
    assert boot.healthy


async def test_auto_bootstrap_false_runs_nothing_either() -> None:
    channel, units, loader, kept = FakeChannel(), Units(), Loader(), KeepAlive()
    boot = bootstrap(
        channel,
        settings=AcpSettings(auto_bootstrap=False),
        units=units,
        loader=loader,
        keep_alive=kept,
    )
    boot.start("s")
    await boot.before_first_prompt(context())
    assert units.writes == [] and loader.calls == [] and kept.attached == [] == kept.probes


async def test_no_services_named_runs_nothing() -> None:
    channel, units = FakeChannel(), Units()
    await run(bootstrap(channel, settings=AcpSettings(services=()), units=units))
    assert units.writes == []


async def test_first_load_notices_the_unload_commands() -> None:
    channel, units, loader, kept = FakeChannel(), Units(), Loader(), KeepAlive()
    boot = bootstrap(channel, units=units, loader=loader, keep_alive=kept)

    await run(boot)

    assert units.writes == [(("hub", "worker"), "always")]
    assert loader.calls == [("load", HUB), ("load", WORKER)]
    assert final(channel)["status"] == "completed"
    notice = channel.texts[-1]
    assert f"`{HUB}`" in notice and f"`{WORKER}`" in notice
    assert "launchd gui/501" in notice
    assert f"launchctl bootout gui/501/{HUB}" in notice
    assert f"launchctl bootout gui/501/{WORKER}" in notice
    assert "`vibey acp unload`" in notice
    assert "auto_services = false" in notice and "your own vibey.toml" in notice
    assert kept.managed == [({HUB: PATHS[HUB], WORKER: PATHS[WORKER]}, HUB, [])]
    assert boot.healthy


async def test_existing_running_labels_are_left_alone_and_said_nothing_new() -> None:
    channel, kept = FakeChannel(), KeepAlive()
    loader = Loader(running={HUB, WORKER})
    units = Units(actions={"hub": "unchanged", "worker": "unchanged"})

    await run(bootstrap(channel, units=units, loader=loader, keep_alive=kept))

    assert loader.calls == []
    assert not any("unload" in text for text in channel.texts)
    assert "already running" in final(channel)["content"][0]["content"]["text"]
    assert kept.managed[0][0] == {HUB: PATHS[HUB], WORKER: PATHS[WORKER]}


async def test_already_loaded_is_said_and_managed_but_not_noticed_as_new() -> None:
    channel = FakeChannel()
    loader = Loader()
    loader.already = {HUB, WORKER}
    await run(bootstrap(channel, loader=loader))
    assert "already loaded" in final(channel)["content"][0]["content"]["text"]
    assert not any("unload" in text for text in channel.texts)


async def test_running_detached_hub_defers_the_hub_unit() -> None:
    channel, kept = FakeChannel(), KeepAlive()
    loader = Loader()
    units = Units(pid=4242)

    await run(bootstrap(channel, units=units, loader=loader, keep_alive=kept))

    assert ("load", "dev.vibey.hub") not in loader.calls
    assert ("load", WORKER) in loader.calls
    shown = final(channel)["content"][0]["content"]["text"]
    assert "outside the service manager" in shown and "4242" in shown
    assert kept.managed == [({HUB: PATHS[HUB], WORKER: PATHS[WORKER]}, HUB, [HUB])]
    assert "outside the service manager" not in channel.texts[-1]  # the notice names the worker
    assert HUB not in channel.texts[-1]


async def test_a_stale_serving_record_whose_hub_does_not_answer_is_loaded_over() -> None:
    # A pid that lives but is no hub (reused, or the hub is wedged): not "running outside".
    channel, loader = FakeChannel(), Loader()
    hub = Hub(up=False, after=1)  # the first probe is the defer check; it answers once loaded
    await run(bootstrap(channel, units=Units(pid=4242), loader=loader, hub=hub))
    assert ("load", HUB) in loader.calls


async def test_an_edited_unit_is_neither_loaded_nor_kept_alive() -> None:
    channel, loader, kept = FakeChannel(), Loader(), KeepAlive()
    units = Units(actions={"worker": "kept-differing"})

    boot = bootstrap(channel, units=units, loader=loader, keep_alive=kept)
    await run(boot)

    assert ("load", WORKER) not in loader.calls
    assert kept.managed[0][0] == {HUB: PATHS[HUB]}
    assert "kept as you edited it" in final(channel)["content"][0]["content"]["text"]
    assert final(channel)["status"] == "completed"
    assert boot.healthy


async def test_a_unit_that_could_not_be_written_or_loaded_fails_the_step() -> None:
    channel, loader = FakeChannel(), Loader()
    loader.fail = {HUB}
    units = Units(actions={"worker": "failed"})

    boot = bootstrap(channel, units=units, loader=loader)
    await run(boot)

    update = final(channel)
    shown = update["content"][0]["content"]["text"]
    assert update["status"] == "failed"
    assert "could not be loaded" in shown and "was not written" in shown
    assert "<b>" not in shown and "<i>" not in shown  # the machine's text is escaped
    assert not boot.healthy


async def test_paths_no_unit_could_run_with_are_said_and_nothing_is_loaded() -> None:
    channel, loader, units = FakeChannel(), Loader(), Units()
    units.error = ValueError("vibey is not on PATH: set [supervisor] vibey <to its full path>")

    boot = bootstrap(channel, units=units, loader=loader)
    await run(boot)

    shown = final(channel)["content"][0]["content"]["text"]
    assert final(channel)["status"] == "failed" and "vibey is not on PATH" in shown
    assert "\\<to its full path\\>" in shown  # escaped: the machine's text is no markup
    assert loader.calls == []
    assert not boot.healthy


async def test_unavailable_service_manager_falls_back_to_hub_start_once() -> None:
    channel, units = FakeChannel(), Units()
    loader = Loader(available=False)
    boot = bootstrap(channel, units=units, loader=loader, hub=Hub(up=False))

    await run(boot)
    assert units.started == 1 and units.writes == [] and loader.calls == []
    assert "cannot keep its services running here" in channel.texts[-1]
    assert "launchd gui/501" in channel.texts[-1]
    assert boot.healthy  # the hub started; nothing more can be done here

    boot._healthy = False  # type: ignore[attr-defined]  # a later session runs the steps again
    await run(boot, "s2")
    assert units.started == 1
    assert "already started the hub once" in final(channel)["content"][0]["content"]["text"]


async def test_a_failed_fallback_start_is_said_and_unhealthy() -> None:
    channel, units = FakeChannel(), Units()
    units.start_works = False
    boot = bootstrap(channel, units=units, loader=Loader(available=False))
    await run(boot)
    assert final(channel)["status"] == "failed"
    assert "that failed" in channel.texts[-1]
    assert not boot.healthy


async def test_the_hub_is_polled_until_it_answers() -> None:
    channel, slept = FakeChannel(), []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    hub = Hub(up=False, after=3)
    boot = bootstrap(channel, hub=hub, settings=AcpSettings(live_poll_seconds=0.5), sleep=sleep)
    await run(boot)
    assert final(channel)["status"] == "completed"
    assert slept == [0.5, 0.5, 0.5]


async def test_a_hub_that_never_answers_within_the_bound_fails_the_step_after_saying_it_all() -> (
    None
):
    channel, kept = FakeChannel(), KeepAlive()

    @contextlib.asynccontextmanager
    async def short(seconds: float) -> AsyncIterator[None]:
        async with asyncio.timeout(0.05):
            yield

    async def sleep(seconds: float) -> None:
        await asyncio.sleep(0.01)

    boot = bootstrap(channel, hub=Hub(up=False), keep_alive=kept, step_timeout=short, sleep=sleep)
    await run(boot)
    update = final(channel)
    shown = update["content"][0]["content"]["text"]
    assert update["status"] == "failed"
    assert "did not finish within" in shown and "may still be starting" in shown
    # The units were loaded: the keep-alive has them and the unload commands were said.
    assert kept.managed and any("launchctl bootout" in text for text in channel.texts)
    assert not boot.healthy


async def test_another_window_holding_the_lock_past_the_bound_loads_nothing() -> None:
    channel, units, loader = FakeChannel(), Units(), Loader()
    boot = bootstrap(channel, units=units, loader=loader, lock=Lock(free=False))
    await run(boot)
    assert units.writes == [] and loader.calls == []
    assert final(channel)["status"] == "failed"
    assert "Another vibey acp" in final(channel)["content"][0]["content"]["text"]
    assert not boot.healthy


async def test_the_lock_is_waited_for_within_the_bootstrap_bound() -> None:
    lock = Lock()
    await run(
        bootstrap(FakeChannel(), lock=lock, settings=AcpSettings(bootstrap_timeout_seconds=9))
    )
    assert lock.holds == [9]


async def test_every_prompt_probes_the_keep_alive_first_and_sessions_attach_and_detach() -> None:
    channel, kept = FakeChannel(), KeepAlive()
    boot = bootstrap(channel, keep_alive=kept)
    await run(boot)

    await boot.before_first_prompt(context("s"))
    await boot.before_first_prompt(context("s"))
    assert kept.probes == ["s", "s"]
    assert kept.attached == ["s"]

    boot.forget("s")
    assert kept.detached == ["s"]
    await boot.close()
    assert kept.stopped
    boot.start("t")  # closed: nothing attaches any more
    assert kept.attached == ["s"]


async def test_without_a_keep_alive_the_services_step_still_runs() -> None:
    channel, loader = FakeChannel(), Loader()
    boot = bootstrap(channel, loader=loader)
    await run(boot)
    await boot.before_first_prompt(context("s"))
    boot.forget("s")
    await boot.close()
    assert loader.calls == [("load", HUB), ("load", WORKER)]


async def test_only_the_worker_named_plans_only_the_worker_and_no_hub_poll() -> None:
    channel, units, hub, kept = FakeChannel(), Units(), Hub(up=False), KeepAlive()
    boot = bootstrap(
        channel,
        settings=AcpSettings(services=("worker",)),
        units=units,
        hub=hub,
        keep_alive=kept,
    )
    await run(boot)
    assert units.writes == [(("worker",), "always")]
    assert hub.probes == 0
    assert kept.managed == [({WORKER: PATHS[WORKER]}, None, [])]


async def test_the_restart_policy_is_the_settings() -> None:
    units = Units()
    await run(bootstrap(FakeChannel(), units=units, settings=AcpSettings(restart="on-failure")))
    assert units.writes == [(("hub", "worker"), "on-failure")]


async def test_without_a_loader_there_is_no_services_step() -> None:
    channel = FakeChannel()
    chosen = AcpSettings()
    boot = AcpBootstrap(
        chosen, None, None, None, channel, AcpUpdateMapper(), Lock(), AcpModes(chosen)
    )
    await run(boot)
    assert services_updates(channel) == []
    assert boot.healthy


# -- fix round 2: root, a worker that would only crash, a write that breaks -------------------


async def test_a_root_process_loads_nothing_and_starts_no_hub() -> None:
    channel, units, loader = FakeChannel(), Units(), Loader()
    loader.refusal = "vibey acp is running as root"
    boot = bootstrap(channel, units=units, loader=loader)
    await run(boot)
    assert units.writes == [] and loader.calls == [] and units.started == 0
    assert final(channel)["status"] == "failed"
    assert "root" in final(channel)["content"][0]["content"]["text"]
    assert not boot.healthy


async def test_a_worker_without_a_database_is_neither_written_nor_loaded() -> None:
    channel, units, loader, kept = FakeChannel(), Units(), Loader(), KeepAlive()
    units.waits = {"worker": "set VIBEY_PG_URL in /home/op/supervisor.env"}
    boot = bootstrap(channel, units=units, loader=loader, keep_alive=kept)

    await run(boot)

    assert units.writes == [(("hub",), "always")]
    assert loader.calls == [("load", HUB)]
    shown = final(channel)["content"][0]["content"]["text"]
    assert final(channel)["status"] == "completed"
    assert "worker: not loaded yet" in shown and "supervisor.env" in shown
    assert kept.managed == [({HUB: PATHS[HUB]}, HUB, [])]
    assert not boot.healthy  # the next session tries the worker again


async def test_a_unit_file_that_cannot_be_written_closes_the_call_failed() -> None:
    channel, units, loader = FakeChannel(), Units(), Loader()
    units.error = PermissionError(13, "Permission denied: '/home/op/Library/Logs/vibey'")
    boot = bootstrap(channel, units=units, loader=loader)
    await run(boot)
    update = final(channel)
    assert update["status"] == "failed"
    assert "PermissionError" in update["content"][0]["content"]["text"]
    assert loader.calls == []
