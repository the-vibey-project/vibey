# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpSearxngStep`, the bootstrap's step 5: offer once to install the local SearXNG, and install
only on the client's explicit "Install SearXNG" (ADR-0102).

Held here, through the real `AcpBootstrap` and its machine turn: `never`, `auto_services = false`
and observe install nothing; a cancel, a timeout, a reject or an unknown option installs nothing;
a SearXNG of the person's own, one already answering, or one vibey installed before means no
question; no runtime is one notice; a second window asks nothing; a failure says one cleaned
reason; a cancel during an allowed install keeps the machine until it ends; and a loaded session
never offers. Every runtime and service-manager call is faked. Module-level test functions
(ADR-0016)."""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import threading
from collections.abc import AsyncIterator, Iterable, Mapping
from typing import Any

import pytest
from acp_fakes import FakeChannel, context

from vibey.application.acp.acp_bootstrap import AcpBootstrap
from vibey.application.acp.acp_searxng_step import (
    INSTALL_OPTION,
    NO_RUNTIME,
    NOT_NOW_OPTION,
    TOOL_SEARXNG,
    UPDATE_OPTION,
    AcpSearxngStep,
)
from vibey.application.acp.dto import SearxngOffer, SearxngPrepared, UnitOutcome
from vibey.application.acp.interfaces.acp_searxng_step_interface import AcpSearxngStepInterface
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper

LABEL = "dev.vibey.searxng"
UNIT = "/home/op/Library/LaunchAgents/dev.vibey.searxng.plist"
RUNTIME = "/opt/homebrew/bin/podman"


class Provisioner:
    def __init__(
        self,
        *,
        runtime: str | None = RUNTIME,
        own_url: str | None = None,
        answering: bool = False,
        provisioned: bool = False,
        prepared: SearxngPrepared | None = None,
        answers_after: int = 1,
    ) -> None:
        self.found = SearxngOffer(runtime, own_url, answering, provisioned, "fc1d81d7e9d0", 28180)
        self.prepared = prepared or SearxngPrepared(True, "Pulled the image; wrote the settings.")
        self.answers_after = answers_after
        self.offers = 0
        self.prepares = 0
        self.probes = 0
        self.after_prepare: SearxngOffer | None = None
        self.gate: threading.Event | None = None
        self.taken = ""

    def offer(self) -> SearxngOffer:
        self.offers += 1
        return self.found

    def provisioned(self) -> bool:
        return self.found.provisioned

    def prepare(self) -> SearxngPrepared:
        self.prepares += 1
        if self.gate is not None:
            self.gate.wait(5)
        return self.prepared

    def answering(self) -> bool:
        self.probes += 1
        return 0 < self.answers_after <= self.probes

    def remove_container(self) -> str:
        return ""

    def record(self) -> None:
        return None

    def refusal(self) -> str:
        return ""

    def image_present(self) -> bool:
        return False

    def purge(self) -> list[str]:
        return []

    def disabled(self) -> bool:
        return self.found.disabled

    def disable(self) -> None:
        self.found = SearxngOffer(
            self.found.runtime,
            self.found.own_url,
            self.found.answering,
            self.found.provisioned,
            self.found.short,
            self.found.port,
            disabled=True,
        )

    def busy(self) -> str:
        return self.taken


class Units:
    def __init__(self, action: str = "created") -> None:
        self.action = action
        self.writes: list[tuple[tuple[str, ...], str]] = []
        self.error: Exception | None = None

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        self.writes.append((names, restart))
        if self.error is not None:
            raise self.error
        detail = "<i>disk \x1b[2Jfull</i>" if self.action == "failed" else ""
        return tuple(UnitOutcome(LABEL, UNIT, self.action, detail) for _ in names)  # type: ignore[arg-type]

    def waiting(self, name: str) -> str:
        return ""

    def recorded(self) -> tuple[str, ...]:
        return ()

    def remove(self, label: str) -> UnitOutcome:
        return UnitOutcome(label, "", "absent")

    def label(self, name: str) -> str:
        return f"dev.vibey.{name}"

    def detached_hub_pid(self) -> int | None:
        return None

    def start_hub(self) -> bool:
        return True


class Loader:
    def __init__(self, *, available: bool = True, running: bool = False) -> None:
        self.is_available = available
        self.running = running
        self.calls: list[tuple[str, str]] = []
        self.fail = ""
        self.refusal = ""

    def refused(self) -> str:
        return self.refusal

    def available(self) -> bool:
        return self.is_available

    def state(self, label: str) -> str:
        return "running" if self.running else "not loaded"

    def load(self, label: str, unit: str) -> UnitOutcome:
        self.calls.append(("load", label))
        if self.fail:
            return UnitOutcome(label, unit, "failed", self.fail)
        return UnitOutcome(label, unit, "loaded")

    def restart(self, label: str) -> UnitOutcome:
        self.calls.append(("restart", label))
        return UnitOutcome(label, UNIT, "restarted")

    def unload(self, label: str) -> UnitOutcome:
        return UnitOutcome(label, UNIT, "unloaded")

    def forget_unit_files(self) -> UnitOutcome:
        return UnitOutcome("", "", "unchanged")

    def unload_commands(self, labels: Iterable[str]) -> tuple[str, ...]:
        return tuple(f"launchctl bootout gui/501/{label}" for label in labels)

    def domain(self) -> str:
        return "launchd gui/501"


class KeepAlive:
    def __init__(self) -> None:
        self.added: list[dict[str, str]] = []

    def add(self, units: Mapping[str, str]) -> None:
        self.added.append(dict(units))

    def manage(self, units: Mapping[str, str], *, hub_label: str | None, deferred: Any) -> None:
        pass

    def attach(self, session_id: str) -> None:
        pass

    def detach(self, session_id: str) -> None:
        pass

    def handed_over(self) -> None:
        pass

    async def probe(self, context: Any = None) -> None:
        pass

    async def stop(self) -> None:
        pass


class Lock:
    def __init__(self, *, free: bool = True) -> None:
        self.free = free
        self.acquired = 0
        self.released = 0

    def acquire(self) -> bool:
        if self.free:
            self.acquired += 1
        return self.free

    def release(self) -> None:
        self.released += 1

    @contextlib.asynccontextmanager
    async def _held(self) -> AsyncIterator[bool]:
        yield True

    def hold(self, timeout: float) -> Any:
        return self._held()


async def _no_sleep(seconds: float) -> None:
    await asyncio.sleep(0)


class World:
    """One bootstrap with only step 5, and every double it drives."""

    def __init__(
        self,
        *,
        settings: AcpSettings | None = None,
        provisioner: Provisioner | None = None,
        units: Units | None = None,
        loader: Loader | None = None,
        lock: Lock | None = None,
        **seams: Any,
    ) -> None:
        self.settings = settings or AcpSettings()
        self.channel = FakeChannel()
        self.provisioner = provisioner or Provisioner()
        self.units = units or Units()
        self.loader = loader or Loader()
        self.lock = lock or Lock()
        self.keep_alive = KeepAlive()
        mapper, modes = AcpUpdateMapper(), AcpModes(self.settings)
        self.step = AcpSearxngStep(
            self.settings,
            self.provisioner,
            self.units,
            self.loader,
            self.channel,
            mapper,
            modes,
            keep_alive=self.keep_alive,  # type: ignore[arg-type]
            sleep=seams.pop("sleep", _no_sleep),
            **seams,
        )
        self.boot = AcpBootstrap(
            self.settings,
            None,
            None,
            None,
            self.channel,
            mapper,
            self.lock,
            modes,
            searxng=self.step,
        )

    async def prompt(self, session_id: str = "s", *, mode_id: str = "drive") -> None:
        await self.boot.before_first_prompt(context(session_id, mode_id=mode_id))

    def calls(self) -> list[dict[str, Any]]:
        return [u for u in self.channel.updates if u.get("toolCallId") == TOOL_SEARXNG]

    def final(self) -> dict[str, Any]:
        return self.calls()[-1]

    def shown(self) -> str:
        content = self.final().get("content") or []
        return "\n".join(part["content"]["text"] for part in content)

    @property
    def installed(self) -> bool:
        return self.provisioner.prepares > 0 or bool(self.units.writes) or bool(self.loader.calls)

    def balanced(self) -> bool:
        return self.lock.acquired == self.lock.released


def test_the_step_is_its_interface() -> None:
    assert isinstance(World().step, AcpSearxngStepInterface)


async def test_only_the_install_option_installs_and_says_each_part() -> None:
    world = World()
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    (asked,) = world.channel.permission_requests
    assert asked["tool_call"]["toolCallId"] == TOOL_SEARXNG
    title = asked["tool_call"]["title"]
    assert "searxng/searxng@sha256:fc1d81d7e9d0" in title and "127.0.0.1:28180" in title
    assert [(o["optionId"], o["kind"]) for o in asked["options"]] == [
        (INSTALL_OPTION, "allow_once"),
        (NOT_NOW_OPTION, "reject_once"),
    ]
    assert world.provisioner.prepares == 1
    assert world.units.writes == [(("searxng",), "always")]
    assert world.loader.calls == [("load", LABEL)]
    assert world.keep_alive.added == [{LABEL: UNIT}]
    assert world.final()["status"] == "completed"
    assert "answers as vibey's own on 127.0.0.1:28180" in world.shown()
    assert any("vibey acp unload" in t and "launchctl bootout" in t for t in world.channel.said)
    # The label is shown exactly, in a code span (review 2 R-2): copied, it names the unit.
    assert any(f"vibey loaded `{LABEL}` into" in t for t in world.channel.said)
    assert world.balanced() and world.lock.acquired == 1
    assert not world.step.pending


@pytest.mark.parametrize("answer", [None, NOT_NOW_OPTION, "bootstrap-postgres:install", "x"])
async def test_anything_but_the_install_option_installs_nothing(answer: str | None) -> None:
    world = World()
    world.channel.permission_answers = [answer] if answer else []

    await world.prompt()

    assert not world.installed
    assert world.final()["status"] == "failed"
    assert any("Brave only as a backup" in t for t in world.channel.said)
    assert world.balanced()
    await world.prompt()  # asked once per process, never again
    assert len(world.channel.permission_requests) == 1


@pytest.mark.parametrize(
    "settings",
    [AcpSettings(searxng="never"), AcpSettings(auto_services=False)],
    ids=["never", "auto_services-off"],
)
async def test_never_and_no_services_grant_run_nothing(settings: AcpSettings) -> None:
    world = World(settings=settings)
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert world.provisioner.offers == 0 and not world.installed
    assert world.channel.updates == [] and world.lock.acquired == 0
    assert not world.step.pending


async def test_observe_asks_nothing_and_a_later_drive_prompt_is_asked() -> None:
    world = World()
    world.channel.permission_answers = [NOT_NOW_OPTION]

    await world.prompt(mode_id="observe")
    assert world.provisioner.offers == 0 and world.channel.updates == []
    assert world.step.pending

    await world.prompt()
    assert len(world.channel.permission_requests) == 1


@pytest.mark.parametrize(
    ("provisioner", "why"),
    [
        (Provisioner(own_url="VIBEY_SEARXNG_URL"), "their own"),
        (Provisioner(answering=True), "already answering"),
        (Provisioner(provisioned=True), "installed before"),
    ],
)
async def test_nothing_is_asked_when_a_searxng_is_already_there(
    provisioner: Provisioner, why: str
) -> None:
    world = World(provisioner=provisioner)
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert world.channel.permission_requests == [] and not world.installed, why
    assert world.channel.updates == [] and world.lock.acquired == 0
    assert not world.step.pending


async def test_no_runtime_is_one_notice_with_the_install_hint_and_nothing_else() -> None:
    world = World(provisioner=Provisioner(runtime=None))

    await world.prompt()
    await world.prompt()

    assert world.channel.said == [NO_RUNTIME]
    assert "podman" in NO_RUNTIME.lower() and "vibey searxng install" in NO_RUNTIME
    assert world.channel.permission_requests == [] and not world.installed
    assert world.lock.acquired == 0


async def test_a_second_window_holding_the_lock_means_this_one_asks_nothing() -> None:
    world = World(lock=Lock(free=False))

    await world.prompt()

    assert world.channel.permission_requests == [] and not world.installed
    assert any("lock is held" in t for t in world.channel.said)


async def test_a_window_that_waited_finds_it_installed_and_asks_nothing() -> None:
    provisioner = Provisioner()
    looks = iter([provisioner.found, SearxngOffer(RUNTIME, None, True, True, "x", 28180)])
    provisioner.offer = lambda: next(looks)  # type: ignore[method-assign]
    world = World(provisioner=provisioner)

    await world.prompt()

    assert world.channel.permission_requests == [] and not world.installed
    assert world.lock.acquired == 1 and world.balanced()


async def test_two_prompts_at_once_are_asked_once() -> None:
    world = World()
    world.channel.permission_block = True

    first = asyncio.create_task(world.prompt("s"))
    await world.channel.permission_asked.wait()
    await asyncio.wait_for(world.prompt("s2"), timeout=5)
    world.channel.cancel_permissions("s")
    await first

    assert len(world.channel.permission_requests) == 1 and not world.installed
    assert world.balanced()


async def test_a_cancel_before_the_question_leaves_it_to_the_next_prompt() -> None:
    world = World()
    ctx = context("s")
    ctx.state.request_cancel()

    await world.boot.before_first_prompt(ctx)

    assert world.channel.permission_requests == [] and world.final()["status"] == "failed"
    assert "Not asked" in world.shown() and world.balanced()
    world.channel.permission_answers = [NOT_NOW_OPTION]
    await world.prompt()
    assert len(world.channel.permission_requests) == 1


async def test_a_cancel_while_asked_installs_nothing_and_is_not_asked_again() -> None:
    world = World()
    world.channel.permission_block = True

    asking = asyncio.create_task(world.prompt())
    await world.channel.permission_asked.wait()
    world.channel.cancel_permissions("s")
    asking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asking

    assert not world.installed and world.final()["status"] == "failed"
    assert world.balanced()
    await world.prompt()
    assert len(world.channel.permission_requests) == 1


async def test_a_switch_to_observe_while_asked_installs_nothing() -> None:
    world = World()
    ctx = context("s")

    async def answer(*args: Any, **kwargs: Any) -> str:
        ctx.mode_id = "observe"
        return INSTALL_OPTION

    world.channel.request_permission = answer  # type: ignore[method-assign]
    await world.boot.before_first_prompt(ctx)

    assert not world.installed and world.final()["status"] == "failed"


async def test_a_failed_download_says_one_cleaned_reason_and_writes_no_unit() -> None:
    prepared = SearxngPrepared(False, "podman pull: \x1b]52;c;evil\x07denied <b>x</b>")
    world = World(provisioner=Provisioner(prepared=prepared))
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert world.units.writes == [] and world.loader.calls == []
    assert world.final()["status"] == "failed"
    assert "\x1b" not in world.shown() and "\x07" not in world.shown()
    assert "denied" in world.shown()
    assert any("not set up" in t and "Brave only as a backup" in t for t in world.channel.said)
    assert world.balanced()


async def test_a_download_that_may_still_run_says_so() -> None:
    prepared = SearxngPrepared(False, "podman did not finish", still_running=True)
    world = World(provisioner=Provisioner(prepared=prepared))
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert "may still be running" in world.shown()


@pytest.mark.parametrize(
    ("action", "said"),
    [("kept-differing", "kept as you edited it"), ("failed", "was not written")],
)
async def test_a_unit_vibey_may_not_load_is_never_loaded(action: str, said: str) -> None:
    world = World(units=Units(action))
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert world.loader.calls == [] and world.keep_alive.added == []
    assert said in world.shown() and world.final()["status"] == "failed"
    assert "\x1b" not in world.shown()


async def test_a_unit_write_that_raises_fails_the_call() -> None:
    units = Units()
    units.error = ValueError("[acp] service_workdir /x is not a folder")
    world = World(units=units)
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert "No unit was written" in world.shown() and world.loader.calls == []


@pytest.mark.parametrize(
    ("loader", "said"),
    [
        (Loader(available=False), "vibey searxng serve"),
        (Loader(), "could not be loaded"),
    ],
)
async def test_a_unit_that_cannot_be_loaded_says_why(loader: Loader, said: str) -> None:
    if loader.is_available:
        loader.fail = "`bootstrap` exited 5: <b>EIO</b>"
    world = World(loader=loader)
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert said in world.shown() and world.keep_alive.added == []


async def test_running_as_root_loads_nothing() -> None:
    loader = Loader()
    loader.refusal = "vibey acp does not load units as root"
    world = World(loader=loader)
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert loader.calls == [] and "root" in world.shown()


async def test_a_unit_running_already_is_restarted_not_loaded_and_kept_alive() -> None:
    """Review 2 (N-a): restarted, so it mounts the settings just written and runs the pinned
    image."""
    world = World(loader=Loader(running=True))
    world.channel.permission_answers = [INSTALL_OPTION]

    await world.prompt()

    assert world.loader.calls == [("restart", LABEL)]
    assert world.keep_alive.added == [{LABEL: UNIT}]
    assert world.final()["status"] == "completed"


async def test_a_searxng_that_never_answers_as_vibeys_own_fails_within_the_bound() -> None:
    world = World(provisioner=Provisioner(answers_after=0))
    world.channel.permission_answers = [INSTALL_OPTION]

    @contextlib.asynccontextmanager
    async def short(seconds: float) -> AsyncIterator[None]:
        async with asyncio.timeout(0.05):
            yield

    world.step._step_timeout = short  # type: ignore[attr-defined]
    await world.prompt()

    assert "did not answer as vibey's own" in world.shown()
    assert world.final()["status"] == "failed" and world.provisioner.probes >= 1


async def test_a_cancel_during_an_allowed_install_keeps_the_machine_until_it_ends() -> None:
    provisioner = Provisioner()
    provisioner.gate = threading.Event()
    world = World(provisioner=provisioner)
    world.channel.permission_answers = [INSTALL_OPTION]

    prompt = asyncio.create_task(world.prompt())
    for _ in range(1000):
        if provisioner.prepares:
            break
        await asyncio.sleep(0.001)
    prompt.cancel()
    with pytest.raises(asyncio.CancelledError):
        await prompt

    assert "goes on in the background" in world.shown()
    assert world.lock.released == 0  # still held by the install
    provisioner.gate.set()
    for _ in range(1000):
        if world.lock.released:
            break
        await asyncio.sleep(0.001)
    assert world.balanced() and world.units.writes == [(("searxng",), "always")]
    for _ in range(100):
        if any("has ended" in t for t in world.channel.said):
            break
        await asyncio.sleep(0.001)
    assert any("has ended: it finished" in t for t in world.channel.said)
    await world.boot.close()


async def test_a_look_that_overruns_is_said_once_and_asks_nothing() -> None:
    @contextlib.asynccontextmanager
    async def expired(seconds: float) -> AsyncIterator[None]:
        async with asyncio.timeout(0):
            yield

    world = World(step_timeout=expired)
    await world.prompt()
    await world.prompt()

    assert world.channel.permission_requests == [] and not world.installed
    assert len([t for t in world.channel.said if "could not check" in t]) == 1


async def test_a_defect_in_the_step_never_fails_the_prompt() -> None:
    world = World()

    def broken() -> SearxngOffer:
        raise RuntimeError("boom")

    world.provisioner.offer = broken  # type: ignore[method-assign]
    await world.prompt()

    assert any("could not check its local SearXNG: RuntimeError" in t for t in world.channel.said)


async def test_a_loaded_session_never_offers() -> None:
    world = World()
    world.channel.permission_answers = [INSTALL_OPTION]

    world.boot.start("loaded")  # session/load and resume start steps 1 to 3 only
    await asyncio.sleep(0)

    assert world.provisioner.offers == 0 and world.channel.permission_requests == []
    await world.boot.close()


# -- step 3 keeps a SearXNG vibey installed before running, like the hub (ADR-0101) ----------


class Managing(KeepAlive):
    def __init__(self) -> None:
        super().__init__()
        self.managed: list[dict[str, str]] = []

    def manage(self, units: Mapping[str, str], *, hub_label: str | None, deferred: Any) -> None:
        self.managed.append(dict(units))


class Hub:
    async def healthy(self) -> bool:
        return True


async def _step_three(
    settings: AcpSettings, *, disabled: bool = False, channel: FakeChannel | None = None
) -> tuple[Units, Loader, Managing, Provisioner]:
    channel = channel or FakeChannel()
    units, loader, keep_alive = Units(), Loader(), Managing()
    provisioner = Provisioner(provisioned=True)
    if disabled:
        provisioner.disable()
    mapper, modes = AcpUpdateMapper(), AcpModes(settings)
    step = AcpSearxngStep(settings, provisioner, units, loader, channel, mapper, modes)
    boot = AcpBootstrap(
        settings,
        None,
        None,
        None,
        channel,
        mapper,
        Lock(),
        modes,
        units=units,
        loader=loader,
        hub=Hub(),  # type: ignore[arg-type]
        keep_alive=keep_alive,  # type: ignore[arg-type]
        searxng=step,
        sleep=_no_sleep,
    )
    boot.start("s")
    steps = boot._steps  # type: ignore[attr-defined]
    assert steps is not None
    await asyncio.wait({steps}, timeout=5)
    await boot.close()
    return units, loader, keep_alive, provisioner


async def test_step_three_loads_and_keeps_a_provisioned_searxng_like_the_hub() -> None:
    units, loader, keep_alive, provisioner = await _step_three(AcpSettings(services=()))

    assert units.writes == [(("searxng",), "always")]
    assert loader.calls == [("load", LABEL)]
    assert keep_alive.managed == [{LABEL: UNIT}]
    assert provisioner.prepares == 0  # nothing is downloaded at a session's start


@pytest.mark.parametrize(
    "settings",
    [AcpSettings(services=(), searxng="never"), AcpSettings(services=(), auto_services=False)],
    ids=["never", "auto_services-off"],
)
async def test_step_three_leaves_searxng_alone_without_the_grant(settings: AcpSettings) -> None:
    units, loader, keep_alive, _ = await _step_three(settings)
    assert units.writes == [] and loader.calls == [] and keep_alive.managed == []


# -- the edges of the step --------------------------------------------------------------------


async def test_a_machine_busy_in_this_window_leaves_the_offer_to_the_next_prompt() -> None:
    uses: list[float] = []

    @contextlib.asynccontextmanager
    async def second_expires(seconds: float) -> AsyncIterator[None]:
        uses.append(seconds)
        async with asyncio.timeout(0 if len(uses) == 2 else None):
            yield

    world = World(step_timeout=second_expires)

    async def never() -> tuple[bool, str | None]:
        await asyncio.Event().wait()
        return True, None

    await world.step.offer(
        context("s"), enter=never, leave=lambda: None, notify=world.channel.notify_update
    )

    assert any("still busy in this window" in t for t in world.channel.said)
    assert world.step.pending and world.channel.permission_requests == []


async def test_an_install_that_breaks_says_so_and_lets_the_machine_go() -> None:
    world = World()
    world.channel.permission_answers = [INSTALL_OPTION]

    def broken() -> SearxngPrepared:
        raise RuntimeError("boom")

    world.provisioner.prepare = broken  # type: ignore[method-assign]
    await world.prompt()

    assert "The install broke: RuntimeError" in world.shown()
    await asyncio.sleep(0)
    assert world.balanced()


async def test_a_cancel_that_lands_with_the_allow_installs_nothing() -> None:
    world = World()
    ctx = context("s")

    async def allow_then_cancel(*args: Any, **kwargs: Any) -> str:
        ctx.state.request_cancel()
        return INSTALL_OPTION

    world.channel.request_permission = allow_then_cancel  # type: ignore[method-assign]
    await world.boot.before_first_prompt(ctx)

    assert not world.installed and world.final()["status"] == "failed"


async def test_a_cancel_before_the_question_is_sent_says_not_asked() -> None:
    world = World()
    world.channel.hold_before[1] = asyncio.Event()  # the tool call waits for the write lock
    prompt = asyncio.create_task(world.prompt())
    await world.channel.write_waiting.wait()
    prompt.cancel()
    with pytest.raises(asyncio.CancelledError):
        await prompt
    assert world.channel.permission_requests == [] and not world.installed
    assert world.balanced()


async def test_a_unit_found_loaded_is_kept_without_a_load_notice() -> None:
    world = World()
    world.channel.permission_answers = [INSTALL_OPTION]

    def already(label: str, unit: str) -> UnitOutcome:
        return UnitOutcome(label, unit, "already-loaded")

    world.loader.load = already  # type: ignore[method-assign]
    await world.prompt()

    assert world.final()["status"] == "completed"
    assert not any("vibey acp unload" in t for t in world.channel.said)


async def test_without_a_keep_alive_the_install_still_completes() -> None:
    world = World()
    world.step._keep_alive = None  # type: ignore[attr-defined]
    world.channel.permission_answers = [INSTALL_OPTION]
    await world.prompt()
    assert world.final()["status"] == "completed"


async def test_an_allowed_install_that_fails_after_a_cancel_is_said_late() -> None:
    provisioner = Provisioner()
    provisioner.gate = threading.Event()
    world = World(provisioner=provisioner)
    world.channel.permission_answers = [INSTALL_OPTION]
    real_prepare = provisioner.prepare

    def failing() -> SearxngPrepared:
        real_prepare()
        raise RuntimeError("pull died")

    provisioner.prepare = failing  # type: ignore[method-assign]
    prompt = asyncio.create_task(world.prompt())
    for _ in range(1000):
        if provisioner.prepares:
            break
        await asyncio.sleep(0.001)
    prompt.cancel()
    with pytest.raises(asyncio.CancelledError):
        await prompt
    provisioner.gate.set()
    for _ in range(1000):
        if any("has ended: it failed" in t for t in world.channel.said):
            break
        await asyncio.sleep(0.001)
    assert any("has ended: it failed" in t for t in world.channel.said)
    assert world.balanced()


async def test_close_silences_a_late_notice_still_being_sent() -> None:
    provisioner = Provisioner()
    provisioner.gate = threading.Event()
    world = World(provisioner=provisioner)
    world.channel.permission_answers = [INSTALL_OPTION]
    prompt = asyncio.create_task(world.prompt())
    for _ in range(1000):
        if provisioner.prepares:
            break
        await asyncio.sleep(0.001)
    prompt.cancel()
    with pytest.raises(asyncio.CancelledError):
        await prompt
    real_notify = world.channel.notify_update

    async def hold_the_late_one(session_id: str, update: Mapping[str, Any]) -> None:
        if "has ended" in str(update):
            await asyncio.Event().wait()  # the late notice never gets its write
        await real_notify(session_id, update)

    world.channel.notify_update = hold_the_late_one  # type: ignore[method-assign]
    provisioner.gate.set()
    for _ in range(1000):
        if world.step._late:  # type: ignore[attr-defined]
            break
        await asyncio.sleep(0.001)
    assert world.step._late  # type: ignore[attr-defined]
    await world.boot.close()
    assert not world.step._late  # type: ignore[attr-defined]


async def test_an_unknown_mode_may_run_nothing() -> None:
    world = World()
    await world.prompt(mode_id="no-such-mode")
    assert world.provisioner.offers == 0 and world.channel.updates == []


# -- fix round 1 ----------------------------------------------------------------------------------


async def test_an_occupied_port_is_said_once_and_installs_nothing() -> None:
    world = World()
    world.provisioner.taken = "something already listens on 127.0.0.1:28180 (\x1b[2Ja dev server)"
    await world.prompt()
    await world.prompt()
    busy = [t for t in world.channel.said if "already listens" in t]
    assert len(busy) == 1 and "\x1b" not in busy[0]
    assert world.channel.permission_requests == [] and not world.installed
    assert world.lock.acquired == 0 and not world.step.pending


async def test_a_searxng_stopped_for_good_is_never_offered_again() -> None:
    world = World()
    world.provisioner.disable()
    world.channel.permission_answers = [INSTALL_OPTION]
    await world.prompt()
    assert world.channel.permission_requests == [] and not world.installed
    assert not world.step.pending


async def test_step_three_never_reloads_a_searxng_stopped_for_good() -> None:
    units, loader, keep_alive, _ = await _step_three(AcpSettings(services=()), disabled=True)
    assert units.writes == [] and loader.calls == [] and keep_alive.managed == []


async def test_never_with_one_installed_says_it_keeps_running_from_its_unit_once() -> None:
    channel = FakeChannel()
    await _step_three(AcpSettings(services=(), searxng="never"), channel=channel)
    said = [t for t in channel.said if 'searxng = "never"' in t]
    assert len(said) == 1 and "vibey searxng uninstall" in said[0]


async def test_never_with_it_stopped_says_nothing() -> None:
    channel = FakeChannel()
    await _step_three(AcpSettings(services=(), searxng="never"), channel=channel, disabled=True)
    assert channel.said == []


def test_held_back_is_empty_when_offered_or_not_installed() -> None:
    world = World()
    assert world.step.held_back() == ""
    never = World(settings=AcpSettings(searxng="never"))
    assert never.step.held_back() == ""  # nothing installed: nothing held back


async def test_the_never_notice_is_said_once_per_process() -> None:
    channel = FakeChannel()
    settings = AcpSettings(services=(), searxng="never")
    provisioner = Provisioner(provisioned=True)
    mapper, modes = AcpUpdateMapper(), AcpModes(settings)
    step = AcpSearxngStep(settings, provisioner, Units(), Loader(), channel, mapper, modes)
    boot = AcpBootstrap(
        settings,
        None,
        None,
        None,
        channel,
        mapper,
        Lock(),
        modes,
        units=Units(),
        loader=Loader(),
        hub=Hub(),  # type: ignore[arg-type]
        searxng=step,
    )
    await boot._services("s")  # type: ignore[attr-defined]
    await boot._services("s2")  # type: ignore[attr-defined]
    assert len([t for t in channel.said if 'searxng = "never"' in t]) == 1


# -- fix round 2: the update an earlier pin gets (review 2, R1) ----------------------------------


def _outdated(**changes: object) -> Provisioner:
    provisioner = Provisioner(provisioned=True, answering=True)
    provisioner.found = dataclasses.replace(
        provisioner.found, outdated="abababababab -> fc1d81d7e9d0", **changes
    )
    return provisioner


async def test_an_earlier_pin_is_offered_as_an_update_and_restarts_the_running_unit() -> None:
    world = World(provisioner=_outdated(), loader=Loader(running=True))
    world.channel.permission_answers = [UPDATE_OPTION]

    await world.prompt()

    (asked,) = world.channel.permission_requests
    title = asked["tool_call"]["title"]
    assert title.startswith("Update vibey's SearXNG") and "abababababab -> fc1d81d7e9d0" in title
    assert [o["optionId"] for o in asked["options"]] == [UPDATE_OPTION, NOT_NOW_OPTION]
    assert [o["name"] for o in asked["options"]] == ["Update", "Not now"]
    assert world.provisioner.prepares == 1
    assert world.loader.calls == [("restart", LABEL)]
    assert world.final()["status"] == "completed"


@pytest.mark.parametrize("answer", [None, NOT_NOW_OPTION, INSTALL_OPTION])
async def test_anything_but_update_leaves_the_old_container_running(answer: str | None) -> None:
    world = World(provisioner=_outdated(), loader=Loader(running=True))
    world.channel.permission_answers = [answer] if answer else []
    await world.prompt()
    assert not world.installed  # nothing pulled, written, loaded or restarted
    assert world.final()["status"] == "failed"
    await world.prompt()
    assert len(world.channel.permission_requests) == 1  # once per process


async def test_an_earlier_pin_is_never_offered_in_observe_or_when_stopped() -> None:
    world = World(provisioner=_outdated())
    await world.prompt(mode_id="observe")
    stopped = World(provisioner=_outdated(disabled=True))
    await stopped.prompt()
    assert world.channel.permission_requests == [] and stopped.channel.permission_requests == []


async def test_a_running_unit_that_will_not_restart_fails_the_update() -> None:
    world = World(provisioner=_outdated(), loader=Loader(running=True))
    world.channel.permission_answers = [UPDATE_OPTION]

    def refuse(label: str) -> UnitOutcome:
        return UnitOutcome(label, UNIT, "failed", "kickstart exited 3")

    world.loader.restart = refuse  # type: ignore[method-assign]
    await world.prompt()
    assert "could not be restarted: kickstart exited 3" in world.shown()
    assert world.final()["status"] == "failed"
