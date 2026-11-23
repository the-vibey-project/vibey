# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey hub start | stop | status`: the one hub on this computer, from a command (#1186).

The operating system is stood in for by a fake that holds the set of live process ids, so
these tests are about what the commands decide: idempotent start, a stop that never
forces, and a stale record never read as a running hub.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vibey.cli import hub_engine as module
from vibey.cli.hub_engine import HUB_ENGINE, HubEngineCommand
from vibey.cli.interfaces.hub_engine_interface import HubEngineCommandInterface
from vibey.cli.main import app
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

runner = CliRunner()


class Clock:
    """Time that only moves when something sleeps."""

    def __init__(self) -> None:
        self.now = 0.0
        self.on_sleep: list[Callable[[], None]] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        for hook in self.on_sleep:
            hook()


class Processes:
    """The operating system, as far as the commands can tell."""

    def __init__(self, store: LocalTokenStore, clock: Clock) -> None:
        self.store = store
        self.clock = clock
        self.live: set[int] = set()
        self.locked: int | None = None
        """The pid holding the hub's lock, as `ServeLock.held_by` would say."""
        self.spawned: list[tuple[Sequence[str], Path]] = []
        self.cwd: list[Path] = []
        self.terminated: list[int] = []
        # How a spawned hub behaves: "serves" writes its record, "dies" exits at once,
        # "hangs" never says where it listens; a stopped one goes away at "stops_after".
        self.spawn_mode = "serves"
        self.spawned_pid = 9001
        self.stops_after: float | None = 0.0

    def hub(self, pid: int) -> None:
        """A hub running as `pid`: alive, and holding its lock."""
        self.live.add(pid)
        self.locked = pid

    def holder(self, state: Path) -> int | None:
        return self.locked

    def alive(self, pid: int) -> bool:
        if pid in self.terminated and self.stops_after is not None:
            return self.clock.now < self.stops_after
        return pid in self.live

    def terminate(self, pid: int) -> bool:
        self.terminated.append(pid)
        if self.stops_after is not None:
            self.stops_after = self.clock.now + self.stops_after
        return pid in self.live

    def spawn(self, argv: Sequence[str], log: Path, *, cwd: Path) -> int:
        self.spawned.append((argv, log))
        self.cwd.append(cwd)
        if self.spawn_mode == "serves":
            self.hub(self.spawned_pid)
            self.store.record_serving(ServingRecord("127.0.0.1", 8765, self.spawned_pid))
        elif self.spawn_mode == "hangs":
            self.hub(self.spawned_pid)
        elif self.spawn_mode == "late":
            # The hub takes its lock, then a moment to open the database before it says where
            # it listens.
            self.hub(self.spawned_pid)
            self.clock.on_sleep.append(
                lambda: self.store.record_serving(
                    ServingRecord("127.0.0.1", 8765, self.spawned_pid)
                )
            )
        return self.spawned_pid


def _setup(tmp_path: Path) -> tuple[HubEngineCommand, Processes, LocalTokenStore, Clock]:
    state = tmp_path / "state"
    (tmp_path / "vibey.toml").write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    clock = Clock()
    processes = Processes(store, clock)
    command = HubEngineCommand(
        config_path=lambda: tmp_path / "vibey.toml",
        processes=processes,
        argv=("vibey-test", "serve"),
        sleep=clock.sleep,
        clock=clock,
        holder=processes.holder,
    )
    return command, processes, store, clock


def _exit(call: object) -> int:
    with pytest.raises(typer.Exit) as caught:
        call()  # type: ignore[operator]
    return int(caught.value.exit_code)


def test_the_command_meets_its_declared_seam() -> None:
    assert isinstance(HUB_ENGINE, HubEngineCommandInterface)


def test_status_of_no_hub_exits_3(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    command, *_ = _setup(tmp_path)
    assert _exit(command.status) == 3
    assert "hub is not running" in capsys.readouterr().out


def test_status_of_a_running_hub_says_where_it_listens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.hub(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.status()
    assert "http://127.0.0.1:8765/api/v1 (pid 77)" in capsys.readouterr().out
    store.record_serving(ServingRecord("::1", 9000, 77, tls=True))
    command.status()
    assert "https://[::1]:9000/api/v1 (pid 77)" in capsys.readouterr().out


def test_a_record_whose_process_is_gone_is_stale_never_a_running_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, _, store, _ = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    assert _exit(command.status) == 3
    assert "stale record from pid 77" in capsys.readouterr().out


def test_an_unreadable_record_is_said_and_is_not_a_running_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, _, store, _ = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    (tmp_path / "state" / "serving.json").write_text("[]")
    assert _exit(command.status) == 3
    assert "hub record unreadable" in capsys.readouterr().err


def test_an_unreadable_vibey_toml_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, *_ = _setup(tmp_path)
    (tmp_path / "vibey.toml").write_text("[hub]\nlan = 'yes'\n")
    assert _exit(command.status) == 2
    assert capsys.readouterr().err


def test_start_launches_the_hub_detached_and_reports_where_it_listens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, *_ = _setup(tmp_path)
    command.start(15)
    assert processes.spawned == [(("vibey-test", "serve"), tmp_path / "state" / "hub.log")]
    assert "hub started: http://127.0.0.1:8765/api/v1 (pid 9001)" in capsys.readouterr().out


def test_start_does_not_start_a_second_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.hub(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.start(15)
    assert processes.spawned == []
    assert "hub already running: http://127.0.0.1:8765/api/v1 (pid 77)" in capsys.readouterr().out


def test_start_names_a_hub_another_process_won_the_race_for(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.spawn_mode = "dies"
    processes.hub(55)
    original = processes.spawn

    def race(argv: Sequence[str], log: Path, *, cwd: Path) -> int:
        store.record_serving(ServingRecord("127.0.0.1", 8765, 55))
        return original(argv, log, cwd=cwd)

    processes.spawn = race  # type: ignore[method-assign]
    command.start(15)
    assert "(another process won the start)" in capsys.readouterr().out


def test_start_waits_past_a_stale_record_left_by_an_earlier_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 5))
    processes.spawn_mode = "late"
    command.start(15)
    out = capsys.readouterr().out
    assert "stale record from pid 5" in out
    assert "hub started: http://127.0.0.1:8765/api/v1 (pid 9001)" in out


def test_start_waits_past_a_record_it_cannot_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 5))
    (tmp_path / "state" / "serving.json").write_text("[]")
    processes.spawn_mode = "late"
    command.start(15)
    captured = capsys.readouterr()
    assert "hub record unreadable" in captured.err
    assert "hub started" in captured.out


def test_start_reports_a_hub_that_exits_before_it_is_ready(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, *_ = _setup(tmp_path)
    processes.spawn_mode = "dies"
    assert _exit(lambda: command.start(15)) == 1
    assert "exited before it was ready" in capsys.readouterr().err


def test_start_reports_a_hub_that_never_says_where_it_listens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, *_ = _setup(tmp_path)
    processes.spawn_mode = "hangs"
    assert _exit(lambda: command.start(1)) == 1
    assert "did not come up within 1s (pid 9001 is still starting)" in capsys.readouterr().err


def test_stop_of_no_hub_is_not_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    command, processes, *_ = _setup(tmp_path)
    command.stop(15)
    assert processes.terminated == []
    assert "hub is not running" in capsys.readouterr().out


def test_stop_asks_the_hub_to_stop_and_waits_for_it_to_go(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.hub(77)
    processes.stops_after = 0.3
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.stop(15)
    assert processes.terminated == [77]
    assert "hub stopped (pid 77)" in capsys.readouterr().out


def test_stop_never_forces_a_hub_that_is_slow_to_go(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.hub(77)
    processes.stops_after = None
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    assert _exit(lambda: command.stop(1)) == 1
    assert processes.terminated == [77]
    assert "is not being forced" in capsys.readouterr().err


def test_the_three_commands_are_on_vibey_hub(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float | None]] = []

    class Recorder:
        def status(self) -> None:
            calls.append(("status", None))

        def start(self, timeout: float) -> None:
            calls.append(("start", timeout))

        def stop(self, timeout: float) -> None:
            calls.append(("stop", timeout))

    monkeypatch.setattr(module, "HUB_ENGINE", Recorder())
    assert runner.invoke(app, ["hub", "status"]).exit_code == 0
    assert runner.invoke(app, ["hub", "start", "--timeout", "3"]).exit_code == 0
    assert runner.invoke(app, ["hub", "stop"]).exit_code == 0
    assert calls == [("status", None), ("start", 3.0), ("stop", module.DEFAULT_TIMEOUT)]


# -- Task 11a fix round: your own hub, and a signal only to its lock holder (M-1, M-2) ----------


def test_a_hostile_folders_record_is_never_read_signalled_or_started_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A cloned repository's vibey.toml names a state folder with a planted record whose pid
    is alive, and the lock probe says that pid holds the lock: were the folder's `[hub]` read,
    `stop` would signal it and `status` would report it. `vibey hub` reads the person's own
    state folder instead, which has no record (Task 11b, review 2 N2-6)."""
    mine = tmp_path / "config"
    mine.mkdir()
    (mine / "vibey.toml").write_text(f"[hub]\nstate_dir = '{tmp_path / 'my-state'}'\n")
    monkeypatch.setattr(module, "acp_user_config", lambda: mine / "vibey.toml")
    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "vibey.toml").write_text("[hub]\nstate_dir = '.hub'\n")
    planted = LocalTokenStore(clone / ".hub")
    planted.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    monkeypatch.chdir(clone)
    clock = Clock()
    processes = Processes(LocalTokenStore(tmp_path / "my-state"), clock)
    processes.hub(77)
    command = HubEngineCommand(
        processes=processes, sleep=clock.sleep, clock=clock, holder=lambda state: 77
    )
    command.stop(1)
    assert processes.terminated == [] and "hub is not running" in capsys.readouterr().out
    assert _exit(command.status) == 3
    processes.spawn_mode = "dies"
    _exit(lambda: command.start(1))
    assert processes.cwd == [mine]
    assert processes.spawned[0][1] == tmp_path / "my-state" / "hub.log"


@pytest.mark.parametrize(
    "record",
    [
        {"host": "127.0.0.1", "port": 8765, "pid": -1},
        {"host": "127.0.0.1", "port": 8765, "pid": 0},
        {"host": "127.0.0.1", "port": 8765, "pid": 1},
        {"host": "127.0.0.1", "port": 8765, "pid": True},
        {"host": "127.0.0.1", "port": 0, "pid": 77},
        {"host": "127.0.0.1", "port": 70000, "pid": 77},
        {"host": "127.0.0.1", "port": True, "pid": 77},
    ],
)
def test_a_record_naming_no_hubs_pid_or_port_is_refused_and_nothing_signalled(
    tmp_path: Path, record: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> None:
    """`kill(-1)` is every process of this account, `kill(0)` its own group: such a record is
    malformed, and `stop` signals nothing."""
    import json

    command, processes, store, _ = _setup(tmp_path)
    for pid in (-1, 0, 1, 77):
        processes.hub(pid)
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "serving.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="process id|port"):
        store.serving()
    command.stop(1)
    assert processes.terminated == []
    assert "hub record unreadable" in capsys.readouterr().err


def test_a_live_pid_whose_lock_nobody_holds_is_stale_and_never_signalled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.live.add(77)  # alive -- a reused pid, say -- but no hub holds the lock
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.stop(1)
    assert processes.terminated == []
    assert "stale record from pid 77" in capsys.readouterr().out


def _real_lock(tmp_path: Path) -> tuple[HubEngineCommand, Processes, LocalTokenStore]:
    """`HubEngineCommand` with the real lock probe; the lock is taken in this process."""
    import os

    state = tmp_path / "state"
    (tmp_path / "vibey.toml").write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    clock = Clock()
    processes = Processes(store, clock)
    processes.live.add(os.getpid())
    command = HubEngineCommand(
        config_path=lambda: tmp_path / "vibey.toml",
        processes=processes,
        sleep=clock.sleep,
        clock=clock,
    )
    return command, processes, store


def test_stop_signals_the_process_holding_the_hubs_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import os

    from vibey.infrastructure.hub.serve_lock import ServeLock

    command, processes, store = _real_lock(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, os.getpid()))
    lock = ServeLock(tmp_path / "state")
    assert lock.acquire()
    try:
        command.status()
        command.stop(1)
    finally:
        lock.release()
    assert processes.terminated == [os.getpid()]  # the fake records it: no real signal
    out = capsys.readouterr().out
    assert f"(pid {os.getpid()})" in out and "hub stopped" in out


def test_a_lock_held_by_another_pid_than_the_record_names_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import os

    from vibey.infrastructure.hub.serve_lock import ServeLock

    command, processes, store = _real_lock(tmp_path)
    processes.live.add(4242)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 4242))
    lock = ServeLock(tmp_path / "state")
    assert lock.acquire()  # held by this process, not by 4242
    try:
        assert _exit(lambda: command.stop(1)) == 1
        assert _exit(command.status) == 1
        assert _exit(lambda: command.start(1)) == 1
    finally:
        lock.release()
    assert processes.terminated == [] and processes.spawned == []
    err = capsys.readouterr().err
    assert f"held by pid {os.getpid()}, but its record names pid 4242" in err
    assert "nothing was signalled" in err


def test_start_launches_the_hub_in_the_persons_configuration_folder(tmp_path: Path) -> None:
    command, processes, *_ = _setup(tmp_path)
    command.start(15)
    assert processes.cwd == [tmp_path]  # the folder holding the vibey.toml it read


def test_start_never_takes_a_stale_record_for_the_hub_it_launched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """While it waits, a record whose lock nobody holds is never the new hub, said or not."""
    command, processes, store, _ = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 5))
    processes.spawn_mode = "dies"
    assert _exit(lambda: command.start(15)) == 1
    captured = capsys.readouterr()
    assert captured.out.count("stale record from pid 5") == 1  # said once, before the start
    assert "exited before it was ready" in captured.err


# -- Task 11b: a hub starting over a stale record is "starting", never a disagreement (N2-3) ----


def _starting_over_a_stale_record(
    tmp_path: Path,
) -> tuple[HubEngineCommand, Processes, LocalTokenStore, Clock]:
    """An earlier hub (pid 5) died and left its record; a new hub (pid 9001) holds the lock
    and has not yet replaced the record."""
    command, processes, store, clock = _setup(tmp_path)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 5))
    processes.hub(9001)
    return command, processes, store, clock


def test_status_says_a_hub_is_starting_not_that_the_two_disagree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, *_ = _starting_over_a_stale_record(tmp_path)
    assert _exit(command.status) == 3
    captured = capsys.readouterr()
    assert "a hub (pid 9001) is starting" in captured.out
    assert "disagree" not in captured.out + captured.err


def test_stop_of_a_starting_hub_signals_nothing_and_says_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, *_ = _starting_over_a_stale_record(tmp_path)
    assert _exit(lambda: command.stop(1)) == 1
    assert processes.terminated == []
    captured = capsys.readouterr()
    assert (
        "a hub (pid 9001) is starting" in captured.err and "nothing was signalled" in captured.err
    )
    assert "disagree" not in captured.out + captured.err


def test_start_waits_for_a_hub_another_start_launched_instead_of_launching_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, clock = _starting_over_a_stale_record(tmp_path)
    clock.on_sleep.append(lambda: store.record_serving(ServingRecord("127.0.0.1", 8765, 9001)))
    command.start(15)
    assert processes.spawned == []
    captured = capsys.readouterr()
    assert "a hub (pid 9001) is starting" in captured.out
    assert "hub started: http://127.0.0.1:8765/api/v1 (pid 9001)" in captured.out
    assert "disagree" not in captured.out + captured.err


def test_start_reports_a_starting_hub_that_dies_before_it_is_ready(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, *_ = _starting_over_a_stale_record(tmp_path)
    processes.live.discard(9001)  # it dies while `start` waits (the fake still says it holds)
    assert _exit(lambda: command.start(15)) == 1
    assert processes.spawned == []
    assert "exited before it was ready" in capsys.readouterr().err


def test_a_lock_held_before_its_pid_is_written_is_a_starting_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`held_by` says 0 while the holder has not written its pid: starting, even when the
    record's own pid is alive (a reused one, say), and nothing is signalled."""
    command, processes, store, clock = _setup(tmp_path)
    processes.live.add(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    processes.locked = 0
    assert _exit(command.status) == 3
    assert "a hub is starting (its pid is not written yet)" in capsys.readouterr().out
    assert _exit(lambda: command.stop(1)) == 1
    assert processes.terminated == []
    assert _exit(lambda: command.start(1)) == 1  # it never comes up within the bound
    assert processes.spawned == []
    assert "the hub is still starting" in capsys.readouterr().err


def test_a_starting_hub_with_no_pid_yet_that_dies_is_reported_as_gone_at_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SP-ACP Task 11b, review N-3: `start` first sees a hub starting with no pid written; it
    dies (its lock drops) while `start` waits. `start` says so at once, never "still starting"
    after the whole timeout."""
    command, processes, store, clock = _setup(tmp_path)
    processes.live.add(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    processes.locked = 0

    def dies() -> None:
        processes.locked = None

    clock.on_sleep.append(dies)
    assert _exit(lambda: command.start(15)) == 1
    assert clock.now < 1  # one poll, not the whole timeout
    assert processes.spawned == []
    err = capsys.readouterr().err
    assert "exited before it was ready" in err and "still starting" not in err


def test_a_starting_hub_that_writes_its_pid_is_then_watched_by_that_pid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Once the starting hub's pid is written, `start` follows that process: when it dies,
    `start` says the hub exited, rather than waiting out the timeout."""
    command, processes, store, clock = _setup(tmp_path)
    processes.live.add(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    processes.locked = 0
    steps = iter([lambda: processes.live.add(4242), lambda: processes.live.discard(4242)])

    def writes_then_dies() -> None:
        step = next(steps, None)
        if step is not None:
            step()
        processes.locked = 4242

    clock.on_sleep.append(writes_then_dies)
    assert _exit(lambda: command.start(15)) == 1
    assert clock.now < 1
    assert "exited before it was ready" in capsys.readouterr().err


def test_while_start_waits_a_live_record_of_another_pid_is_never_its_hub(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The record names a live process (77) while the lock is the launched hub's (9001): not a
    hub starting over a stale record, so `start` keeps waiting, quietly, and never reports 77."""
    command, processes, store, _ = _setup(tmp_path)
    processes.live.add(77)
    processes.spawn_mode = "hangs"
    original = processes.spawn

    def planted(argv: Sequence[str], log: Path, *, cwd: Path) -> int:
        pid = original(argv, log, cwd=cwd)
        store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
        return pid

    processes.spawn = planted  # type: ignore[method-assign]
    assert _exit(lambda: command.start(1)) == 1
    captured = capsys.readouterr()
    assert "hub started" not in captured.out and "disagree" not in captured.err
    assert "did not come up within 1s (pid 9001 is still starting)" in captured.err
    assert processes.terminated == []
