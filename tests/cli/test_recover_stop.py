# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey recover --stop-workers` says while it stops this user's workers."""

import pytest

from vibey.cli.recover import stop_workers
from vibey.infrastructure.worker_processes import ProcessInfo, StopPlan, StopReport


def _row(pid: int, command: str) -> ProcessInfo:
    return ProcessInfo(pid=pid, ppid=1, uid=501, state="S", argv=tuple(command.split()))


class FakeStopper:
    def __init__(self, plan: StopPlan, report: StopReport | None = None) -> None:
        self._plan = plan
        self._report = report or StopReport((), (), ())
        self.stopped_with: float | None = None
        self.asked: tuple[str | None, bool] | None = None

    def plan(self, project_id: str | None = None, *, include_shared: bool = False) -> StopPlan:
        self.asked = (project_id, include_shared)
        return self._plan

    def stop(self, plan: StopPlan, *, grace_seconds: float) -> StopReport:
        self.stopped_with = grace_seconds
        return self._report


def test_with_no_workers_it_says_so_and_there_is_nothing_to_wait_for(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stopper = FakeStopper(StopPlan((), ()))
    assert stop_workers(stopper, grace_seconds=5, dry_run=False) is True
    assert "no vibey worker processes are running" in capsys.readouterr().out
    assert stopper.stopped_with is None


def test_a_dry_run_lists_the_processes_and_signals_none_of_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan((_row(200, "vibey worker"),), (_row(203, "gptossloop run"),))
    stopper = FakeStopper(plan)

    assert stop_workers(stopper, grace_seconds=5, dry_run=True) is True

    out = capsys.readouterr().out
    assert "would stop these processes:" in out
    assert "worker 200: vibey worker" in out and "started by a worker, 203: gptossloop run" in out
    assert stopper.stopped_with is None


def test_it_stops_what_it_listed_with_the_grace_it_was_given_and_reports_the_outcome(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan((_row(200, "vibey worker"),), ())
    stopper = FakeStopper(plan, StopReport(terminated=(200,), killed=(), survivors=()))

    assert stop_workers(stopper, grace_seconds=7.5, dry_run=False) is True

    out = capsys.readouterr().out
    assert "stopping these processes:" in out
    assert "1 stopped on SIGTERM, 0 needed SIGKILL" in out
    assert stopper.stopped_with == 7.5


def test_a_survivor_is_named_and_the_recovery_is_refused(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan((_row(200, "vibey worker"),), ())
    stopper = FakeStopper(plan, StopReport(terminated=(), killed=(), survivors=(200, 202)))

    assert stop_workers(stopper, grace_seconds=1, dry_run=False) is False

    out = capsys.readouterr().out
    assert "still running after SIGKILL: 200, 202" in out
    assert "Leases were not reset" in out


def test_a_very_long_command_line_is_cut_for_the_terminal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan((_row(200, "vibey worker " + "x" * 400),), ())
    stop_workers(FakeStopper(plan), grace_seconds=1, dry_run=True)
    line = next(line for line in capsys.readouterr().out.splitlines() if "worker 200" in line)
    assert line.endswith("…") and len(line) < 200


def test_a_project_scoped_stop_asks_for_that_project_and_says_when_none_is_running(
    capsys: pytest.CaptureFixture[str],
) -> None:
    stopper = FakeStopper(StopPlan((), ()))
    assert stop_workers(stopper, grace_seconds=5, dry_run=False, project_id="p1") is True
    assert stopper.asked == ("p1", False)
    assert "no vibey worker is running for project p1" in capsys.readouterr().out


def test_a_shared_worker_that_is_left_running_blocks_a_recovery_that_resets_leases(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan(
        (_row(200, "vibey worker --project p1"),), (), (_row(220, "vibey worker --all-projects"),)
    )
    stopper = FakeStopper(plan, StopReport(terminated=(200,), killed=(), survivors=()))

    assert (
        stop_workers(stopper, grace_seconds=5, dry_run=False, project_id="p1", shared_blocks=True)
        is False
    )

    out = capsys.readouterr().out
    assert "1 stopped on SIGTERM" in out
    assert "left running, because it serves more than this project:" in out
    assert "worker 220: vibey worker --all-projects" in out
    assert "Leases were not reset" in out and "--include-shared" in out


def test_a_shared_worker_left_running_does_not_fail_a_retry_or_a_dry_run(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = StopPlan((_row(200, "vibey worker --project p1"),), (), (_row(220, "vibey worker"),))

    assert stop_workers(FakeStopper(plan), grace_seconds=5, dry_run=False, project_id="p1") is True
    assert (
        stop_workers(
            FakeStopper(plan), grace_seconds=5, dry_run=True, project_id="p1", shared_blocks=True
        )
        is True
    )
    assert "Leases were not reset" not in capsys.readouterr().out


def test_including_the_shared_workers_is_passed_on_and_nothing_is_then_left() -> None:
    stopper = FakeStopper(
        StopPlan((_row(200, "vibey worker --all-projects"),), ()), StopReport((200,), (), ())
    )
    assert (
        stop_workers(
            stopper,
            grace_seconds=5,
            dry_run=False,
            project_id="p1",
            include_shared=True,
            shared_blocks=True,
        )
        is True
    )
    assert stopper.asked == ("p1", True)
