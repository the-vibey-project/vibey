# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finding and stopping this user's `vibey worker` processes, against a fake process table."""

import signal
import subprocess
from collections.abc import Sequence

import pytest

from vibey.infrastructure.interfaces.worker_processes_interface import (
    ProcessTableInterface,
    WorkerStopperInterface,
)
from vibey.infrastructure.worker_processes import (
    ProcessInfo,
    PsProcessTable,
    WorkerStopper,
    is_vibey_worker,
)

ME = 501
WORKER = ("/x/.venv/bin/vibey", "-vvv", "worker", "--project", "p")


def _row(
    pid: int, ppid: int, argv: Sequence[str], *, uid: int = ME, state: str = "S"
) -> ProcessInfo:
    return ProcessInfo(pid=pid, ppid=ppid, uid=uid, state=state, argv=tuple(argv))


@pytest.mark.parametrize(
    "argv",
    [
        WORKER,
        ("uv", "run", "vibey", "worker"),
        ("caffeinate", "-i", "uv", "run", "vibey", "-vvv", "worker", "--ignore-sabbath"),
        ("python", "-m", "vibey.cli.main", "worker"),
        ("python", "-m", "vibey", "worker"),
    ],
)
def test_a_vibey_command_line_whose_command_is_worker_is_a_worker(argv: tuple[str, ...]) -> None:
    assert is_vibey_worker(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ("vibey", "status"),
        ("vibey", "recover", "--stop-workers"),
        ("tail", "-f", "worker.log"),
        ("/Users/adam/git/vibey/.venv/bin/python", "script.py", "worker"),
        ("python", "-m", "other.vibey", "worker"),
        ("vim", "vibey"),
        ("worker", "vibey"),
        (),
    ],
)
def test_other_commands_that_merely_mention_the_words_are_not(argv: tuple[str, ...]) -> None:
    assert not is_vibey_worker(argv)


def test_the_process_table_is_read_through_ps_and_odd_rows_are_skipped() -> None:
    calls: list[list[str]] = []
    out = "\n".join(
        [
            "  200     1   501 S    /x/vibey -vvv worker --project 'a b'",
            "  201   200   501 Z    <defunct>",
            '  202   200   501 S    python -c "unbalanced',
            "garbage",
            "  x    1   501 S    /bin/true",
            "",
        ]
    )

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        assert kwargs == {"capture_output": True, "text": True, "check": False}
        return subprocess.CompletedProcess(argv, 0, stdout=out)

    rows = PsProcessTable(run=run).snapshot()

    assert calls == [["ps", "-axo", "pid=,ppid=,uid=,stat=,command="]]
    assert [r.pid for r in rows] == [200, 201, 202]
    assert rows[0].argv == ("/x/vibey", "-vvv", "worker", "--project", "a b")
    assert rows[0].command == "/x/vibey -vvv worker --project a b"
    assert not rows[1].alive and rows[0].alive
    assert rows[2].argv == ("python", "-c", '"unbalanced')


class World:
    """A process table that signals change. `stubborn` ignores SIGTERM, `immortal` ignores both."""

    def __init__(
        self,
        rows: Sequence[ProcessInfo],
        *,
        stubborn: Sequence[int] = (),
        immortal: Sequence[int] = (),
    ) -> None:
        self.rows = {r.pid: r for r in rows}
        self.stubborn = set(stubborn)
        self.immortal = set(immortal)
        self.sent: list[tuple[int, int]] = []
        self.now = 0.0
        self.refuse: dict[int, type[Exception]] = {}

    def snapshot(self) -> Sequence[ProcessInfo]:
        return list(self.rows.values())

    def kill(self, pid: int, sig: int) -> None:
        self.sent.append((pid, sig))
        if pid in self.refuse:
            raise self.refuse[pid]
        if pid not in self.rows:
            raise ProcessLookupError(pid)
        if pid in self.immortal or (sig == signal.SIGTERM and pid in self.stubborn):
            return
        del self.rows[pid]

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def clock(self) -> float:
        return self.now

    def stopper(self, *, pid: int = 100) -> WorkerStopper:
        return WorkerStopper(
            table=self,  # type: ignore[arg-type]
            kill=self.kill,
            sleep=self.sleep,
            clock=self.clock,
            uid=ME,
            pid=pid,
        )


def _machine() -> list[ProcessInfo]:
    return [
        _row(1, 0, ("/sbin/launchd",)),
        _row(90, 1, ("-zsh",)),
        _row(100, 90, ("uv", "run", "vibey", "recover", "--stop-workers")),
        _row(200, 90, ("caffeinate", "-i", "uv", "run", "vibey", "worker")),
        _row(201, 200, ("uv", "run", "vibey", "worker")),
        _row(202, 201, WORKER),
        _row(203, 202, ("gptossloop", "run")),
        _row(204, 203, ("node", "helper")),
        _row(300, 1, WORKER, uid=0),
        _row(400, 1, WORKER, state="Z"),
        _row(500, 202, ("rooty",), uid=0),
        _row(501, 202, ("dead-child",), state="Z"),
    ]


def test_the_plan_names_this_users_live_workers_and_what_they_started() -> None:
    plan = _world_plan()
    assert [r.pid for r in plan.workers] == [200, 201, 202]
    assert [r.pid for r in plan.descendants] == [203, 204]
    assert [r.pid for r in plan.targets] == [200, 201, 202, 203, 204]


def _world_plan():  # type: ignore[no-untyped-def]
    return World(_machine()).stopper().plan()


def test_another_users_zombie_and_foreign_processes_are_never_in_the_plan() -> None:
    pids = {r.pid for r in _world_plan().targets}
    assert not pids & {300, 400, 500, 501}


def test_this_process_and_what_started_it_are_never_stopped_even_when_they_look_like_workers() -> (
    None
):
    rows = [
        _row(90, 1, ("-zsh",)),
        _row(200, 90, ("caffeinate", "-i", "uv", "run", "vibey", "worker")),
        _row(205, 200, ("sh", "-c", "vibey recover")),
        _row(100, 205, ("vibey", "recover", "--stop-workers")),
        _row(210, 90, WORKER),
    ]
    plan = World(rows).stopper(pid=100).plan()
    assert [r.pid for r in plan.workers] == [210]
    assert plan.descendants == ()


def test_no_workers_means_an_empty_plan() -> None:
    plan = World([_row(100, 1, ("vibey", "recover"))]).stopper().plan()
    assert plan.workers == () and plan.descendants == ()


def test_stopping_signals_what_a_worker_started_before_the_worker_and_waits_for_each_to_go() -> (
    None
):
    world = World(_machine())
    stopper = world.stopper()

    report = stopper.stop(stopper.plan(), grace_seconds=10)

    assert [pid for pid, _ in world.sent] == [204, 203, 202, 201, 200]
    assert {sig for _, sig in world.sent} == {signal.SIGTERM}
    assert report.terminated == (200, 201, 202, 203, 204)
    assert report.killed == () and report.survivors == ()
    assert set(world.rows) == {1, 90, 100, 300, 400, 500, 501}


def test_a_process_that_ignores_sigterm_is_killed_after_the_grace_period() -> None:
    world = World(_machine(), stubborn=[203])
    stopper = world.stopper()

    report = stopper.stop(stopper.plan(), grace_seconds=1.0)

    assert report.killed == (203,) and report.survivors == ()
    assert (203, signal.SIGKILL) in world.sent
    assert world.now >= 1.0  # it waited the grace period out before escalating


def test_a_process_that_survives_even_sigkill_is_reported_not_hidden() -> None:
    world = World(_machine(), immortal=[202])
    stopper = world.stopper()

    report = stopper.stop(stopper.plan(), grace_seconds=0.5)

    assert report.survivors == (202,)
    assert report.killed == ()


def test_a_process_that_is_gone_or_not_ours_to_signal_does_not_stop_the_rest() -> None:
    world = World(_machine())
    world.refuse = {203: ProcessLookupError, 202: PermissionError}
    stopper = world.stopper()

    report = stopper.stop(stopper.plan(), grace_seconds=0.4)

    assert 202 in report.survivors  # PermissionError: still there, so it is reported
    assert 204 not in report.survivors and 200 not in report.survivors


def test_a_zero_grace_goes_straight_to_sigkill_for_what_is_left() -> None:
    world = World(_machine(), stubborn=[202])
    stopper = world.stopper()
    report = stopper.stop(stopper.plan(), grace_seconds=0)
    assert report.killed == (202,)


def test_the_real_table_and_stopper_keep_their_declared_seams() -> None:
    table = PsProcessTable()
    assert isinstance(table, ProcessTableInterface)
    assert isinstance(WorkerStopper(table=table, uid=ME, pid=1), WorkerStopperInterface)
