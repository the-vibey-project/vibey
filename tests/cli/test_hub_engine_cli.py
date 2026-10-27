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
        self.spawned: list[tuple[Sequence[str], Path]] = []
        self.terminated: list[int] = []
        # How a spawned hub behaves: "serves" writes its record, "dies" exits at once,
        # "hangs" never says where it listens; a stopped one goes away at "stops_after".
        self.spawn_mode = "serves"
        self.spawned_pid = 9001
        self.stops_after: float | None = 0.0

    def alive(self, pid: int) -> bool:
        if pid in self.terminated and self.stops_after is not None:
            return self.clock.now < self.stops_after
        return pid in self.live

    def terminate(self, pid: int) -> bool:
        self.terminated.append(pid)
        if self.stops_after is not None:
            self.stops_after = self.clock.now + self.stops_after
        return pid in self.live

    def spawn(self, argv: Sequence[str], log: Path) -> int:
        self.spawned.append((argv, log))
        if self.spawn_mode == "serves":
            self.live.add(self.spawned_pid)
            self.store.record_serving(ServingRecord("127.0.0.1", 8765, self.spawned_pid))
        elif self.spawn_mode == "hangs":
            self.live.add(self.spawned_pid)
        elif self.spawn_mode == "late":
            # The hub takes a moment to open the database before it says where it listens.
            self.live.add(self.spawned_pid)
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
    processes.live.add(77)
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
    processes.live.add(77)
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.start(15)
    assert processes.spawned == []
    assert "hub already running: http://127.0.0.1:8765/api/v1 (pid 77)" in capsys.readouterr().out


def test_start_names_a_hub_another_process_won_the_race_for(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.spawn_mode = "dies"
    processes.live.add(55)
    original = processes.spawn

    def race(argv: Sequence[str], log: Path) -> int:
        store.record_serving(ServingRecord("127.0.0.1", 8765, 55))
        return original(argv, log)

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
    processes.live.add(77)
    processes.stops_after = 0.3
    store.record_serving(ServingRecord("127.0.0.1", 8765, 77))
    command.stop(15)
    assert processes.terminated == [77]
    assert "hub stopped (pid 77)" in capsys.readouterr().out


def test_stop_never_forces_a_hub_that_is_slow_to_go(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command, processes, store, _ = _setup(tmp_path)
    processes.live.add(77)
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
