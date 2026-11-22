# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpBootstrap`: doctor and connect on first contact, PostgreSQL only on an explicit allow.

The bootstrap changes the machine outside the repository (client config files, a PostgreSQL
install), so most tests here hold a safety rule: nothing installs without the client selecting
the install option, observe mode triggers nothing privileged, a slow step never delays the
`session/new` answer, and nothing runs twice or loops. Module-level test functions rather than
a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import AsyncIterator, Mapping
from typing import Any

import pytest
from acp_fakes import FakeChannel, FakeHub, build_agent, text, until

from vibey.application.acp.acp_bootstrap import (
    INSTALL_COMMAND,
    INSTALL_OPTION,
    NOT_NOW_OPTION,
    AcpBootstrap,
)
from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.application.acp.dto import (
    AcpSessionContext,
    DoctorResult,
    PostgresInstallOutcome,
    PostgresReadiness,
)
from vibey.application.acp.interfaces.acp_bootstrap_interface import AcpBootstrapInterface
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.session_state import AcpSessionState
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper

# -- doubles -------------------------------------------------------------------------------


class LoggingChannel(FakeChannel):
    """A channel that also logs, in one list, each update and each response the test notes."""

    def __init__(self) -> None:
        super().__init__()
        self.log: list[tuple[str, str]] = []

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        await super().notify_update(session_id, update)
        self.log.append(("update", str(update["sessionUpdate"])))

    def tool_updates(self, tool_call_id: str) -> list[dict[str, Any]]:
        return [u for u in self.updates if u.get("toolCallId") == tool_call_id]


class Probe:
    def __init__(self, name: str, *results: DoctorResult, hold: asyncio.Event | None = None):
        self.name = name
        self._results = results
        self._hold = hold
        self.ran = 0

    async def run(self) -> tuple[DoctorResult, ...]:
        self.ran += 1
        if self._hold is not None:
            await self._hold.wait()
        return self._results


class Connector:
    def __init__(self, *results: DoctorResult, connected: bool = False) -> None:
        self.results = results or (DoctorResult("PASS", "cursor", "updated ~/.cursor/mcp.json"),)
        self.connected = connected
        self.calls = 0

    async def connect_detected(self) -> tuple[DoctorResult, ...]:
        self.calls += 1
        self.connected = True  # the marker is written
        return self.results

    def already_connected(self) -> bool:
        return self.connected


class Postgres:
    def __init__(
        self,
        *,
        ready: bool = False,
        package_manager: str | None = "apt-get",
        outcome: PostgresInstallOutcome | None = None,
    ) -> None:
        self.ready = ready
        self.package_manager = package_manager
        self.outcome = outcome or PostgresInstallOutcome(
            ok=True, detail="apt-get installed/started PostgreSQL", needs_password=False
        )
        self.status_calls = 0
        self.installs = 0

    def status(self) -> PostgresReadiness:
        self.status_calls += 1
        return PostgresReadiness(
            ready=self.ready,
            detail="PostgreSQL client tools are not installed",
            package_manager=self.package_manager,
        )

    def install(self) -> PostgresInstallOutcome:
        self.installs += 1
        return self.outcome


class Lock:
    def __init__(self, *, free: bool = True, error: OSError | None = None) -> None:
        self.free = free
        self.error = error
        self.acquired = 0
        self.released = 0

    def acquire(self) -> bool:
        if self.error is not None:
            raise self.error
        if self.free:
            self.acquired += 1
        return self.free

    def release(self) -> None:
        self.released += 1


async def _timed_out(task: asyncio.Future[Any], seconds: float) -> bool:
    return False


@contextlib.asynccontextmanager
async def _expires_at_once(seconds: float) -> AsyncIterator[None]:
    async with asyncio.timeout(0):
        yield


def bootstrap(
    channel: FakeChannel,
    *,
    settings: AcpSettings | None = None,
    probes: tuple[Probe, ...] | None = None,
    connector: Connector | None = None,
    postgres: Postgres | None = None,
    lock: Lock | None = None,
    **seams: Any,
) -> AcpBootstrap:
    chosen = settings or AcpSettings()
    return AcpBootstrap(
        chosen,
        DoctorChecks(probes if probes is not None else (Probe("p", PASSED),)),
        connector,
        postgres,
        channel,
        AcpUpdateMapper(),
        lock or Lock(),
        AcpModes(chosen),
        **seams,
    )


PASSED = DoctorResult("PASS", "hub-exposure", "loopback only", ("PASS hub-exposure  loopback",))
FAILED = DoctorResult("FAIL", "ledger-guard", "the app role owns the ledger")


def session(session_id: str = "s", *, mode_id: str = "drive") -> AcpSessionContext:
    state = AcpSessionState(session_id)
    state.begin_turn("t1")
    return AcpSessionContext(session_id=session_id, state=state, mode_id=mode_id, cwd="/work")


async def finished(boot: AcpBootstrap) -> None:
    await until(lambda: boot.steps_finished)


# -- steps 1 to 3: after the response, in the background -----------------------------------


async def test_session_new_answers_before_slow_bootstrap_finishes() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()  # never set while the request is answered
    boot = bootstrap(channel, probes=(Probe("slow", PASSED, hold=hold),))
    agent = build_agent(channel, FakeHub(), bootstrap=boot)

    response = await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    channel.log.append(("response", "session/new"))  # the peer writes it as the handler returns
    assert response["sessionId"] == "s"
    await until(lambda: ("update", "tool_call") in channel.log)

    assert channel.log.index(("response", "session/new")) < channel.log.index(
        ("update", "tool_call")
    )
    assert not boot.steps_finished  # still waiting on the probe: the answer did not wait for it
    hold.set()
    await finished(boot)
    await agent.close()


async def test_doctor_sends_one_update_per_probe_then_completes() -> None:
    channel = LoggingChannel()
    second = DoctorResult("WARN", "supervisor-worker", "not installed")
    boot = bootstrap(channel, probes=(Probe("a", PASSED), Probe("b", second), Probe("c")))

    boot.start("s")
    await finished(boot)

    updates = channel.tool_updates("bootstrap-doctor")
    assert updates[0]["sessionUpdate"] == "tool_call"
    assert updates[0]["title"] == "vibey doctor" and updates[0]["kind"] == "read"
    progress = updates[1:-1]
    assert [u["status"] for u in progress] == ["in_progress"] * 3
    shown = progress[1]["content"][0]["content"]["text"]
    # Each update carries every result so far, since a client replaces a tool call's content.
    assert "PASS hub-exposure: loopback only" in shown
    assert "WARN supervisor-worker: not installed" in shown
    assert updates[-1]["status"] == "completed"
    assert boot.healthy


async def test_a_failed_check_fails_the_doctor_call_and_a_new_session_runs_it_again() -> None:
    channel = LoggingChannel()
    probe = Probe("db", FAILED)
    boot = bootstrap(channel, probes=(probe,))

    boot.start("s")
    await finished(boot)
    assert channel.tool_updates("bootstrap-doctor")[-1]["status"] == "failed"
    assert not boot.healthy

    boot.start("s2")  # not healthy: a new session tries again, once, never in a loop
    await until(lambda: probe.ran == 2)
    await finished(boot)
    assert probe.ran == 2


async def test_a_healthy_bootstrap_is_not_run_again_and_two_never_run_at_once() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()
    probe = Probe("slow", PASSED, hold=hold)
    boot = bootstrap(channel, probes=(probe,))

    boot.start("s")
    boot.start("s2")  # one is running: this one waits for nothing and starts nothing
    await until(lambda: probe.ran == 1)
    hold.set()
    await finished(boot)
    boot.start("s3")  # finished healthy: a no-op
    await asyncio.sleep(0)

    assert probe.ran == 1
    assert {s for s, u in zip(channel.sessions, channel.updates, strict=True)} == {"s"}


async def test_auto_bootstrap_false_runs_nothing() -> None:
    channel = LoggingChannel()
    probe, connector, postgres = Probe("p", PASSED), Connector(), Postgres()
    boot = bootstrap(
        channel,
        settings=AcpSettings(auto_bootstrap=False),
        probes=(probe,),
        connector=connector,
        postgres=postgres,
    )

    boot.start("s")
    await boot.before_first_prompt(session())

    assert (probe.ran, connector.calls, postgres.status_calls, postgres.installs) == (0, 0, 0, 0)
    assert channel.updates == [] and channel.permission_requests == []
    assert boot.done


async def test_a_step_that_overruns_its_bound_fails_with_a_reason() -> None:
    channel = LoggingChannel()
    boot = bootstrap(
        channel,
        probes=(Probe("slow", PASSED, hold=asyncio.Event()),),
        step_timeout=_expires_at_once,
    )

    boot.start("s")
    await finished(boot)

    last = channel.tool_updates("bootstrap-doctor")[-1]
    assert last["status"] == "failed"
    assert "bootstrap_timeout_seconds" in last["content"][0]["content"]["text"]
    assert not boot.healthy


async def test_check_text_reaches_the_editor_cleaned_bounded_and_on_one_line() -> None:
    channel = LoggingChannel()
    hostile = DoctorResult(
        "WARN", "gate-notices", "see [here](https://evil.example)\n# heading\x1b[31m" + "x" * 900
    )
    boot = bootstrap(channel, probes=(Probe("g", hostile),))

    boot.start("s")
    await finished(boot)

    shown = channel.tool_updates("bootstrap-doctor")[-1]["content"][0]["content"]["text"]
    assert "](https" not in shown and "https://" not in shown
    assert "\x1b" not in shown
    assert "\n#" not in shown  # the newline did not start a heading: the line stayed one line
    assert len(shown) < AcpSettings().live_message_chars * 2


# -- step 2: connect -----------------------------------------------------------------------


async def test_connect_runs_once_and_reports_each_client() -> None:
    channel = LoggingChannel()
    connector = Connector(
        DoctorResult("PASS", "cursor", "updated ~/.cursor/mcp.json"),
        DoctorResult("WARN", "codex", "~/.codex/config.toml: invalid TOML"),
    )
    lock = Lock()
    boot = bootstrap(channel, connector=connector, lock=lock)

    boot.start("s")
    await finished(boot)

    updates = channel.tool_updates("bootstrap-connect")
    assert updates[0]["title"] == "vibey connect" and updates[0]["kind"] == "edit"
    text_shown = updates[-1]["content"][0]["content"]["text"]
    assert "PASS cursor" in text_shown and "WARN codex" in text_shown
    assert updates[-1]["status"] == "completed"  # a WARN for one client is not a failure
    assert connector.calls == 1 and (lock.acquired, lock.released) == (1, 1)


async def test_second_session_skips_connect_by_marker() -> None:
    connector = Connector()
    first = LoggingChannel()
    boot = bootstrap(first, connector=connector)
    boot.start("s")
    await finished(boot)
    assert connector.calls == 1

    # Another `vibey acp` (an editor restarted, a second window): the marker says connected.
    second = LoggingChannel()
    again = bootstrap(second, connector=connector)
    again.start("s")
    await finished(again)

    assert connector.calls == 1
    assert second.tool_updates("bootstrap-connect") == []


async def test_auto_connect_false_never_connects() -> None:
    channel, connector = LoggingChannel(), Connector()
    boot = bootstrap(channel, settings=AcpSettings(auto_connect=False), connector=connector)

    boot.start("s")
    await finished(boot)

    assert connector.calls == 0 and channel.tool_updates("bootstrap-connect") == []


async def test_connect_held_by_another_process_is_left_to_it() -> None:
    channel, connector = LoggingChannel(), Connector()
    boot = bootstrap(channel, connector=connector, lock=Lock(free=False))

    boot.start("s")
    await finished(boot)

    assert connector.calls == 0
    shown = channel.tool_updates("bootstrap-connect")[-1]["content"][0]["content"]["text"]
    assert "Another vibey acp" in shown


async def test_a_lock_that_cannot_be_taken_connects_nothing() -> None:
    channel, connector = LoggingChannel(), Connector()
    boot = bootstrap(channel, connector=connector, lock=Lock(error=PermissionError("read-only")))

    boot.start("s")
    await finished(boot)

    assert connector.calls == 0
    assert channel.tool_updates("bootstrap-connect")[-1]["status"] == "failed"


# -- step 4: PostgreSQL, inside the first prompt, only on an explicit allow ------------------


async def test_postgres_is_asked_inside_the_first_prompt_only() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [NOT_NOW_OPTION]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    boot.start("s")
    assert channel.permission_requests == []  # not at session/new
    await boot.before_first_prompt(session("s"))
    await boot.before_first_prompt(session("s"))
    await boot.before_first_prompt(session("s2"))

    assert (
        channel.permission_requests[0]["session"] == "s" and len(channel.permission_requests) == 1
    )
    asked = channel.permission_requests[0]
    assert asked["tool_call"]["title"] == (
        "Install PostgreSQL with apt-get? On Linux this needs sudo; if sudo asks for a password, "
        "run `vibey doctor --install-postgres` in your own terminal."
    )
    assert asked["options"] == [
        {"optionId": INSTALL_OPTION, "name": "Install PostgreSQL", "kind": "allow_once"},
        {"optionId": NOT_NOW_OPTION, "name": "Not now", "kind": "reject_once"},
    ]
    assert asked["timeout"] == AcpSettings().permission_timeout_seconds
    call = channel.tool_updates("bootstrap-postgres")[0]
    assert (call["title"], call["kind"]) == ("Install PostgreSQL", "execute")
    assert boot.done


async def test_only_the_install_option_installs() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(session())

    assert postgres.installs == 1
    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "completed"
    assert "apt-get installed/started PostgreSQL" in last["content"][0]["content"]["text"]


@pytest.mark.parametrize(
    "answer",
    [NOT_NOW_OPTION, None, "bootstrap-postgres:INSTALL", "allow_once", "Install PostgreSQL", ""],
    ids=["not-now", "timeout-or-cancel", "case-changed", "a-kind", "a-name", "empty"],
)
async def test_anything_but_the_install_option_installs_nothing(answer: str | None) -> None:
    channel = LoggingChannel()
    channel.permission_answers = [answer]  # type: ignore[list-item]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(session())

    assert postgres.installs == 0
    assert channel.tool_updates("bootstrap-postgres")[-1]["status"] == "failed"


async def test_rejected_postgres_continues_degraded_with_a_message() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [NOT_NOW_OPTION]
    boot = bootstrap(channel, postgres=Postgres())

    await boot.before_first_prompt(session())

    said = [t for t in channel.said if "PostgreSQL" in t]
    assert len(said) == 1
    assert "degraded" in said[0] and "not installed" in said[0]
    assert "vibey doctor \\-\\-install\\-postgres" not in said[0]  # trusted text, not escaped
    assert INSTALL_COMMAND in said[0]


async def test_postgres_never_setting_never_asks() -> None:
    channel = LoggingChannel()
    postgres = Postgres()
    boot = bootstrap(channel, settings=AcpSettings(install_postgres="never"), postgres=postgres)

    await boot.before_first_prompt(session())

    assert channel.permission_requests == []
    assert postgres.status_calls == 0 and postgres.installs == 0


async def test_a_ready_postgres_asks_nothing() -> None:
    channel = LoggingChannel()
    postgres = Postgres(ready=True)
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(session())

    assert channel.permission_requests == [] and postgres.installs == 0
    assert channel.updates == []


async def test_observe_mode_triggers_nothing_privileged() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION, INSTALL_OPTION]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(session(mode_id="observe"))
    await boot.before_first_prompt(session(mode_id="observe"))

    assert channel.permission_requests == [] and postgres.installs == 0
    noted = [t for t in channel.said if "observe" in t]
    assert len(noted) == 1  # said once, not on every prompt
    assert not boot.done  # a later prompt in drive may still be asked

    await boot.before_first_prompt(session(mode_id="drive"))
    assert postgres.installs == 1


async def test_a_switch_to_observe_while_asked_installs_nothing() -> None:
    channel = LoggingChannel()
    context = session()

    async def switch_then_allow(*args: Any, **kwargs: Any) -> str | None:
        context.mode_id = "observe"
        return INSTALL_OPTION

    channel.request_permission = switch_then_allow  # type: ignore[method-assign]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(context)

    assert postgres.installs == 0
    assert channel.tool_updates("bootstrap-postgres")[-1]["status"] == "failed"


async def test_sudo_that_needs_a_password_is_reported_with_the_command() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    refused = PostgresInstallOutcome(
        ok=False, detail="apt-get could not refresh package metadata", needs_password=True
    )
    boot = bootstrap(channel, postgres=Postgres(outcome=refused))

    await boot.before_first_prompt(session())

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "failed"
    shown = last["content"][0]["content"]["text"]
    assert "sudo needs a password" in shown
    assert "`vibey doctor --install-postgres`" in shown


async def test_a_failed_install_says_so_and_the_hub_runs_degraded() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    failed = PostgresInstallOutcome(ok=False, detail="dnf could not install", needs_password=False)
    boot = bootstrap(channel, postgres=Postgres(outcome=failed))

    await boot.before_first_prompt(session())

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "failed"
    assert "dnf could not install" in last["content"][0]["content"]["text"]
    assert any("degraded" in t for t in channel.said)


async def test_no_package_manager_asks_nothing_and_says_why() -> None:
    channel = LoggingChannel()
    postgres = Postgres(package_manager=None)
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(session())

    assert channel.permission_requests == [] and postgres.installs == 0
    assert any("no package manager" in t for t in channel.said)


async def test_a_cancel_while_asked_closes_the_call_says_degraded_once_and_is_not_asked_again() -> (
    None
):
    channel = LoggingChannel()
    channel.permission_block = True
    postgres, lock = Postgres(), Lock()
    boot = bootstrap(channel, postgres=postgres, lock=lock)

    asking = asyncio.create_task(boot.before_first_prompt(session()))
    await channel.permission_asked.wait()
    channel.cancel_permissions("s")  # what `session/cancel` does first,
    asking.cancel()  # and then it cancels the turn
    with pytest.raises(asyncio.CancelledError):
        await asking

    assert channel.tool_updates("bootstrap-postgres")[-1]["status"] == "failed"
    assert len([t for t in channel.said if "degraded" in t]) == 1
    assert lock.released == 1
    await boot.before_first_prompt(session())
    assert postgres.installs == 0 and len(channel.permission_requests) == 1


async def test_a_cancel_through_the_agent_while_asked_closes_the_call_with_one_message() -> None:
    channel = LoggingChannel()
    channel.permission_block = True
    boot = bootstrap(channel, postgres=Postgres())
    agent = build_agent(channel, FakeHub(), bootstrap=boot)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    prompt = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("/help")]})
    )
    await asyncio.wait_for(channel.permission_asked.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})

    assert await asyncio.wait_for(prompt, 5) == {"stopReason": "cancelled"}
    statuses = [u.get("status") for u in channel.tool_updates("bootstrap-postgres")]
    assert statuses == ["pending", "failed"]
    assert len([t for t in channel.said if "degraded" in t]) == 1
    await agent.close()


async def test_a_cancel_before_the_question_leaves_step_four_to_the_next_prompt() -> None:
    channel = LoggingChannel()
    entered, release = threading.Event(), threading.Event()

    class SlowCheck(Postgres):
        def status(self) -> PostgresReadiness:
            entered.set()
            release.wait(5)
            return super().status()

    postgres = SlowCheck()
    channel.permission_answers = [NOT_NOW_OPTION]
    boot = bootstrap(channel, postgres=postgres)

    checking = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.to_thread(entered.wait, 5)
    checking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await checking
    release.set()

    assert channel.updates == [] and not boot.done
    await boot.before_first_prompt(session())  # asked now
    assert len(channel.permission_requests) == 1


async def test_two_sessions_prompting_at_once_are_asked_once() -> None:
    channel = LoggingChannel()
    channel.permission_block = True
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    first = asyncio.create_task(boot.before_first_prompt(session("s")))
    await channel.permission_asked.wait()
    await asyncio.wait_for(boot.before_first_prompt(session("s2")), timeout=5)  # never waits

    channel.cancel_permissions("s")
    await first
    assert len(channel.permission_requests) == 1 and postgres.installs == 0


async def test_another_process_setting_up_means_this_one_does_not_ask() -> None:
    channel = LoggingChannel()
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres, lock=Lock(free=False))

    await boot.before_first_prompt(session())

    assert channel.permission_requests == [] and postgres.installs == 0
    assert any("another" in t for t in channel.said)


async def test_a_defect_in_the_postgres_step_never_fails_the_prompt() -> None:
    channel = LoggingChannel()

    class Broken(Postgres):
        def status(self) -> PostgresReadiness:
            raise RuntimeError("which() blew up")

    boot = bootstrap(channel, postgres=Broken())

    await boot.before_first_prompt(session())  # does not raise

    assert any("RuntimeError" in t for t in channel.said)


# -- waiting for steps 1 to 3 before the first prompt -------------------------------------


async def test_bootstrap_timeout_lets_the_prompt_proceed_with_a_notice() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()
    boot = bootstrap(channel, probes=(Probe("slow", PASSED, hold=hold),), wait=_timed_out)

    boot.start("s")
    await boot.before_first_prompt(session())
    await boot.before_first_prompt(session())  # the notice is said once per session

    notices = [t for t in channel.said if "still running" in t]
    assert len(notices) == 1
    hold.set()
    await finished(boot)


async def test_the_first_prompt_waits_for_a_running_bootstrap() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()
    boot = bootstrap(channel, probes=(Probe("slow", PASSED, hold=hold),))

    boot.start("s")
    waiting = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.sleep(0)
    assert not waiting.done()
    hold.set()
    await asyncio.wait_for(waiting, timeout=5)
    assert boot.steps_finished


# -- wired into the agent -------------------------------------------------------------------


async def test_the_agent_starts_the_bootstrap_and_asks_inside_the_first_prompt() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [NOT_NOW_OPTION]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)
    agent = build_agent(channel, FakeHub(), bootstrap=boot)

    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await finished(boot)
    assert channel.permission_requests == []
    result = await agent.handle_request(
        "session/prompt", {"sessionId": "s", "prompt": [text("/help")]}
    )

    assert result == {"stopReason": "end_turn"}
    assert len(channel.permission_requests) == 1
    await agent.close()


def test_the_bootstrap_satisfies_its_interface() -> None:
    assert isinstance(bootstrap(FakeChannel()), AcpBootstrapInterface)


# -- the remaining edges ------------------------------------------------------------------


async def test_without_checks_only_connect_runs() -> None:
    channel, connector = LoggingChannel(), Connector()
    boot = AcpBootstrap(
        AcpSettings(),
        None,
        connector,
        None,
        channel,
        AcpUpdateMapper(),
        Lock(),
        AcpModes(AcpSettings()),
    )

    boot.start("s")
    await finished(boot)

    assert channel.tool_updates("bootstrap-doctor") == []
    assert connector.calls == 1 and boot.healthy and boot.done


async def test_a_connect_cut_off_by_its_bound_holds_the_lock_until_its_thread_ends() -> None:
    release = asyncio.Event()

    class Slow(Connector):
        async def connect_detected(self) -> tuple[DoctorResult, ...]:
            await release.wait()
            return ()

    channel, lock = LoggingChannel(), Lock()
    boot = bootstrap(channel, probes=(), connector=Slow(), lock=lock, step_timeout=_expires_at_once)

    boot.start("s")
    await finished(boot)

    last = channel.tool_updates("bootstrap-connect")[-1]
    assert last["status"] == "failed" and "vibey connect did not finish" in str(last)
    assert lock.released == 0 and not boot.healthy  # still writing: a second window waits
    release.set()
    await until(lambda: lock.released == 1)


async def test_observe_with_postgres_ready_says_nothing() -> None:
    channel = LoggingChannel()
    boot = bootstrap(channel, postgres=Postgres(ready=True))

    await boot.before_first_prompt(session(mode_id="observe"))

    assert channel.updates == []


async def test_a_cancel_before_the_question_installs_nothing() -> None:
    channel = LoggingChannel()
    context = session()
    postgres = Postgres()

    class CancelOnAnnounce(LoggingChannel):
        async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
            await super().notify_update(session_id, update)
            if update.get("toolCallId") == "bootstrap-postgres":
                context.state.request_cancel()

    channel = CancelOnAnnounce()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(context)

    assert channel.permission_requests == [] and postgres.installs == 0
    assert channel.tool_updates("bootstrap-postgres")[-1]["status"] == "failed"


async def test_a_switch_while_the_install_frame_is_written_installs_nothing() -> None:
    context = session()

    class SwitchOnProgress(LoggingChannel):
        async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
            await super().notify_update(session_id, update)
            if update.get("status") == "in_progress":
                context.mode_id = "observe"

    channel = SwitchOnProgress()
    channel.permission_answers = [INSTALL_OPTION]
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    await boot.before_first_prompt(context)

    assert postgres.installs == 0
    assert channel.tool_updates("bootstrap-postgres")[-1]["status"] == "failed"


async def test_a_mode_this_vibey_does_not_offer_may_run_nothing() -> None:
    channel = LoggingChannel()
    postgres = Postgres()
    boot = bootstrap(channel, settings=AcpSettings(modes=("drive",)), postgres=postgres)

    await boot.before_first_prompt(session(mode_id="observe"))

    assert channel.permission_requests == [] and postgres.installs == 0


async def test_a_bootstrap_that_breaks_is_logged_not_left_unread(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Gone(LoggingChannel):
        async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
            raise ConnectionResetError("the editor went away")

    boot = bootstrap(Gone())

    boot.start("s")
    await finished(boot)
    await asyncio.sleep(0)  # the done callback runs right after the task ends

    assert "the ACP bootstrap failed" in caplog.text
    assert not boot.healthy


# -- fix round 1: an allowed install outlives a cancel; the machine; close; load ---------


class BlockingInstall(Postgres):
    """An install that runs on its thread until `finish` is set."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.started, self.finish = threading.Event(), threading.Event()

    def install(self) -> PostgresInstallOutcome:
        self.started.set()
        self.finish.wait(10)
        return super().install()


async def test_a_cancel_during_an_allowed_install_holds_the_lock_until_it_really_ends(
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    postgres, lock = BlockingInstall(), Lock()
    boot = bootstrap(channel, postgres=postgres, lock=lock)

    installing = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.to_thread(postgres.started.wait, 5)
    installing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await installing

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "failed" and "goes on in the background" in str(last)
    assert lock.released == 0  # a second window cannot start a second package-manager run
    postgres.finish.set()
    await until(lambda: lock.released == 1, spins=100_000)
    await until(lambda: any("has ended" in t for t in channel.said), spins=100_000)
    assert "installed/started" in caplog.text
    assert postgres.installs == 1


async def test_an_install_that_ends_after_the_window_closed_is_only_logged() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    postgres, lock = (
        BlockingInstall(outcome=PostgresInstallOutcome(False, "dnf broke", False)),
        Lock(),
    )
    boot = bootstrap(channel, postgres=postgres, lock=lock)
    installing = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.to_thread(postgres.started.wait, 5)
    installing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await installing

    await boot.close()
    postgres.finish.set()
    await until(lambda: lock.released == 1, spins=100_000)

    assert not any("has ended" in t for t in channel.said)


async def test_an_install_that_may_still_be_running_is_not_called_failed() -> None:
    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    unconfirmed = PostgresInstallOutcome(
        ok=False,
        detail="Homebrew could not install PostgreSQL",
        needs_password=False,
        still_running=True,
    )
    boot = bootstrap(channel, postgres=Postgres(outcome=unconfirmed))

    await boot.before_first_prompt(session())

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "completed" and "may still be running" in str(last)
    assert not any("degraded" in t for t in channel.said)


async def test_step_four_waits_for_this_windows_own_connect_never_blaming_another() -> None:
    channel = LoggingChannel()
    release = asyncio.Event()

    class Slow(Connector):
        async def connect_detected(self) -> tuple[DoctorResult, ...]:
            await release.wait()
            return (DoctorResult("PASS", "cursor", "updated"),)

    class FlockLike(Lock):
        """As `flock` on a new descriptor: a second take conflicts, even in this process."""

        held = False

        def acquire(self) -> bool:
            if self.held:
                return False
            self.held = True
            return super().acquire()

        def release(self) -> None:
            self.held = False
            super().release()

    channel.permission_answers = [NOT_NOW_OPTION]
    boot = bootstrap(
        channel, connector=Slow(), postgres=Postgres(), lock=FlockLike(), wait=_timed_out
    )
    boot.start("s")
    await until(lambda: channel.tool_updates("bootstrap-connect") != [])

    asking = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.sleep(0)
    release.set()
    await asyncio.wait_for(asking, 5)

    assert len(channel.permission_requests) == 1
    assert not any("another vibey acp" in t for t in channel.said)


async def test_step_four_that_cannot_get_its_turn_in_time_is_asked_next_prompt() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()

    class Slow(Connector):
        async def connect_detected(self) -> tuple[DoctorResult, ...]:
            await hold.wait()
            return ()

    in_prompt: list[float] = []
    prompting = False

    def third_expires(seconds: float) -> contextlib.AbstractAsyncContextManager[None]:
        # Inside the prompt: 1, the PostgreSQL check; 2, the wait for this window's machine.
        if prompting:
            in_prompt.append(seconds)
        return asyncio.timeout(0 if prompting and len(in_prompt) == 2 else 5)

    boot = bootstrap(
        channel, connector=Slow(), postgres=Postgres(), wait=_timed_out, step_timeout=third_expires
    )
    boot.start("s")
    await until(lambda: channel.tool_updates("bootstrap-connect") != [])

    prompting = True
    await boot.before_first_prompt(session())
    prompting = False

    assert any("own connect step is still running" in t for t in channel.said)
    assert channel.permission_requests == [] and not boot.done
    hold.set()
    await finished(boot)
    channel.permission_answers = [NOT_NOW_OPTION]
    await boot.before_first_prompt(session("s2"))
    assert len(channel.permission_requests) == 1


async def test_a_connect_while_step_four_holds_the_machine_is_not_called_healthy() -> None:
    channel = LoggingChannel()
    channel.permission_block = True
    connector = Connector()
    boot = bootstrap(channel, probes=(), connector=connector, postgres=Postgres())

    asking = asyncio.create_task(boot.before_first_prompt(session()))
    await channel.permission_asked.wait()
    boot.start("s")
    await finished(boot)

    assert connector.calls == 0 and not boot.healthy
    assert "busy with its PostgreSQL step" in str(channel.tool_updates("bootstrap-connect")[-1])
    channel.cancel_permissions("s")
    await asking


async def test_a_check_that_overruns_is_said_once_and_the_prompt_goes_on() -> None:
    channel = LoggingChannel()
    entered, release = threading.Event(), threading.Event()

    class Hung(Postgres):
        def status(self) -> PostgresReadiness:
            entered.set()
            release.wait(5)
            return super().status()

    boot = bootstrap(channel, postgres=Hung(), step_timeout=_expires_at_once)

    await boot.before_first_prompt(session())
    await boot.before_first_prompt(session())
    release.set()

    assert len([t for t in channel.said if "could not check PostgreSQL within" in t]) == 1
    assert channel.permission_requests == [] and boot.done is False  # steps never ran here


async def test_an_observe_check_that_overruns_says_so() -> None:
    channel = LoggingChannel()
    release = threading.Event()

    class Hung(Postgres):
        def status(self) -> PostgresReadiness:
            release.wait(5)
            return super().status()

    boot = bootstrap(channel, postgres=Hung(), step_timeout=_expires_at_once)

    await boot.before_first_prompt(session(mode_id="observe"))
    release.set()

    assert any("could not check PostgreSQL within" in t for t in channel.said)


async def test_close_cancels_the_steps_and_nothing_is_sent_after_it() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()
    probe = Probe("slow", PASSED, hold=hold)
    boot = bootstrap(channel, probes=(probe,))
    boot.start("s")
    await until(lambda: probe.ran == 1)

    await boot.close()
    sent = len(channel.updates)
    boot.start("s2")
    await boot.before_first_prompt(session())

    assert boot.steps_finished and not boot.healthy
    assert len(channel.updates) == sent


async def test_a_session_closed_hears_nothing_more_from_the_bootstrap() -> None:
    channel = LoggingChannel()
    hold = asyncio.Event()
    boot = bootstrap(channel, probes=(Probe("slow", PASSED, hold=hold),))
    agent = build_agent(channel, FakeHub(), bootstrap=boot)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await until(lambda: channel.tool_updates("bootstrap-doctor") != [])

    await agent.handle_request("session/close", {"sessionId": "s"})
    hold.set()
    await finished(boot)

    assert [u["sessionUpdate"] for u in channel.tool_updates("bootstrap-doctor")] == ["tool_call"]
    await agent.close()


async def test_a_load_starts_the_bootstrap_too() -> None:
    channel = LoggingChannel()
    hub = FakeHub()
    hub.kept["0b6e2c2a-3d41-4a8e-9c55-0f7b1f2a9d11"] = ("/work", [])
    boot = bootstrap(channel)
    agent = build_agent(channel, hub, bootstrap=boot)

    await agent.handle_request(
        "session/resume", {"sessionId": "0b6e2c2a-3d41-4a8e-9c55-0f7b1f2a9d11", "cwd": "/work"}
    )
    await finished(boot)

    assert channel.tool_updates("bootstrap-doctor")[0]["title"] == "vibey doctor"
    await agent.close()


async def test_a_cancel_while_the_question_is_announced_closes_it_as_not_asked() -> None:
    channel = LoggingChannel()
    channel.hold_at[1] = asyncio.Event()  # the `bootstrap-postgres` tool call is sent, then waits
    postgres = Postgres()
    boot = bootstrap(channel, postgres=postgres)

    announcing = asyncio.create_task(boot.before_first_prompt(session()))
    await until(lambda: len(channel.updates) == 1)
    announcing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await announcing

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "failed" and "Not asked" in str(last)
    assert channel.permission_requests == [] and not boot.done


async def test_an_allowed_install_that_breaks_after_a_cancel_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Breaks(BlockingInstall):
        def install(self) -> PostgresInstallOutcome:
            super().install()
            raise RuntimeError("the package database is locked")

    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    postgres, lock = Breaks(), Lock()
    boot = bootstrap(channel, postgres=postgres, lock=lock)
    installing = asyncio.create_task(boot.before_first_prompt(session()))
    await asyncio.to_thread(postgres.started.wait, 5)
    installing.cancel()
    with pytest.raises(asyncio.CancelledError):
        await installing

    postgres.finish.set()
    await until(lambda: any("it failed" in t for t in channel.said), spins=100_000)

    assert "the PostgreSQL install allowed over ACP failed" in caplog.text
    assert lock.released == 1


async def test_an_install_that_breaks_closes_its_tool_call() -> None:
    class Breaks(Postgres):
        def install(self) -> PostgresInstallOutcome:
            raise RuntimeError("the package database is locked")

    channel = LoggingChannel()
    channel.permission_answers = [INSTALL_OPTION]
    lock = Lock()
    boot = bootstrap(channel, postgres=Breaks(), lock=lock)

    await boot.before_first_prompt(session())

    last = channel.tool_updates("bootstrap-postgres")[-1]
    assert last["status"] == "failed" and "RuntimeError" in str(last)
    await until(lambda: lock.released == 1)
