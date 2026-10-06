# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`RemoteCommandService`: dispatch, find the run by its id alone, and report it truthfully."""

import pytest

from vibey.application.interfaces import RemoteCommandServiceInterface, RemoteWorkflowForge
from vibey.application.remote_command import RemoteCommandService
from vibey.domain.remote_command import (
    RemoteCommand,
    RemoteCommandRefused,
    RemoteReport,
    RemoteState,
    WorkflowRun,
)

ID = "0123456789abcdef"


class FakeForge:
    """Shows a scripted sequence of runs for the one name it was dispatched."""

    def __init__(self, runs: list[WorkflowRun | None], report: RemoteReport | None = None) -> None:
        self.runs = runs
        self.reported = report
        self.dispatched: list[RemoteCommand] = []
        self.asked: list[str] = []

    async def dispatch(self, command: RemoteCommand) -> None:
        self.dispatched.append(command)

    async def find(self, command_run_name: str) -> WorkflowRun | None:
        self.asked.append(command_run_name)
        return self.runs.pop(0) if len(self.runs) > 1 else self.runs[0]

    async def report(self, run_id: int) -> RemoteReport | None:
        assert run_id == 7
        return self.reported


def run(status: str, conclusion: str | None = None) -> WorkflowRun:
    return WorkflowRun(run_id=7, status=status, conclusion=conclusion, url="https://run/7")


def service(forge: FakeForge, **kwargs: float) -> tuple[RemoteCommandService, list[float]]:
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    return (
        RemoteCommandService(forge, new_id=lambda: ID, sleep=sleep, **kwargs),
        slept,
    )


def test_the_service_and_its_forge_satisfy_their_interfaces() -> None:
    assert isinstance(service(FakeForge([None]))[0], RemoteCommandServiceInterface)
    assert isinstance(FakeForge([None]), RemoteWorkflowForge)


def test_settings_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        RemoteCommandService(FakeForge([None]), new_id=lambda: ID, sleep=None, poll_seconds=0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        RemoteCommandService(FakeForge([None]), new_id=lambda: ID, sleep=None, timeout_seconds=-1)  # type: ignore[arg-type]


async def test_start_dispatches_the_command_under_a_fresh_id() -> None:
    forge = FakeForge([None])
    command = await service(forge)[0].start(["status", "--json"])
    assert command == RemoteCommand(("status", "--json"), ID)
    assert forge.dispatched == [command]


async def test_start_dispatches_under_the_id_the_caller_names() -> None:
    forge = FakeForge([None])
    named = "0123456789abcdef01234567-" + "0" * 32
    command = await service(forge)[0].start(["status"], request_id=named)
    assert command == RemoteCommand(("status",), named)
    assert forge.dispatched == [command]


async def test_a_named_id_that_is_not_a_request_id_is_refused_before_dispatch() -> None:
    forge = FakeForge([None])
    with pytest.raises(RemoteCommandRefused, match="not a request id"):
        await service(forge)[0].start(["status"], request_id="vibey run; rm")
    assert forge.dispatched == []


async def test_a_refused_command_is_never_dispatched() -> None:
    forge = FakeForge([None])
    with pytest.raises(RemoteCommandRefused):
        await service(forge)[0].start(["-w", "status"])
    assert forge.dispatched == []


async def test_a_run_not_yet_shown_is_queued_and_found_by_its_name() -> None:
    forge = FakeForge([None])
    status = await service(forge)[0].poll(ID)
    assert (status.state, status.url) == (RemoteState.QUEUED, "")
    assert forge.asked == [f"vibey {ID}"]


@pytest.mark.parametrize(
    ("forge_status", "state"),
    [
        ("queued", RemoteState.QUEUED),
        ("waiting", RemoteState.QUEUED),
        ("in_progress", RemoteState.RUNNING),
    ],
)
async def test_an_unfinished_run_is_queued_or_running(
    forge_status: str, state: RemoteState
) -> None:
    status = await service(FakeForge([run(forge_status)]))[0].poll(ID)
    assert (status.state, status.url, status.exit_code) == (state, "https://run/7", None)


async def test_a_finished_run_reports_the_commands_own_exit_and_output() -> None:
    forge = FakeForge([run("completed", "success")], RemoteReport(3, "out", "err"))
    status = await service(forge)[0].poll(ID)
    assert status.as_dict() == {
        "request_id": ID,
        "state": "done",
        "url": "https://run/7",
        "exit_code": 3,
        "stdout": "out",
        "stderr": "err",
        "detail": "",
    }


async def test_a_run_that_handed_back_nothing_failed_and_says_how_it_ended() -> None:
    status = await service(FakeForge([run("completed", "cancelled")]))[0].poll(ID)
    assert status.state is RemoteState.FAILED
    assert "ended `cancelled` and handed back no report" in status.detail
    status = await service(FakeForge([run("completed", None)]))[0].poll(ID)
    assert "ended `unknown`" in status.detail


async def test_poll_refuses_an_id_that_is_not_one() -> None:
    with pytest.raises(RemoteCommandRefused):
        await service(FakeForge([None]))[0].poll("not an id")


async def test_run_waits_through_queued_and_running_to_the_report() -> None:
    forge = FakeForge([None, run("queued"), run("in_progress"), run("completed", "success")])
    forge.reported = RemoteReport(0, "ok\n", "")
    svc, slept = service(forge, poll_seconds=5)
    status = await svc.run(["doctor"])
    assert (status.state, status.exit_code, status.stdout) == (RemoteState.DONE, 0, "ok\n")
    assert slept == [5, 5, 5]


async def test_run_stops_waiting_but_says_the_run_carries_on() -> None:
    svc, slept = service(FakeForge([run("in_progress")]), poll_seconds=10, timeout_seconds=25)
    status = await svc.run(["doctor"])
    assert status.state is RemoteState.RUNNING and not status.finished
    assert status.detail == "stopped waiting after 30s; the run carries on at https://run/7"
    assert slept == [10, 10, 10]


async def test_run_that_never_appeared_says_so_without_a_url() -> None:
    svc, _ = service(FakeForge([None]), poll_seconds=10, timeout_seconds=5)
    status = await svc.run(["doctor"])
    assert (status.state, status.detail) == (
        RemoteState.QUEUED,
        "stopped waiting after 10s; the run carries on",
    )
