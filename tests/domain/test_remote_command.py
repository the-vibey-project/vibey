# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey -w`: which tokens carry the flag, what may be sent, and what a run reports."""

import pytest

from vibey.domain.interfaces import RemoteCommandInterface, WorkflowsInvocationInterface
from vibey.domain.remote_command import (
    WORKFLOWS_INVOCATION,
    RemoteCommand,
    RemoteCommandRefused,
    RemoteState,
    RemoteStatus,
)

ID = "0123456789abcdef"


def test_each_satisfies_its_interface() -> None:
    assert isinstance(WORKFLOWS_INVOCATION, WorkflowsInvocationInterface)
    assert isinstance(RemoteCommand(("status",), ID), RemoteCommandInterface)


@pytest.mark.parametrize(
    ("argv", "remote", "forwarded"),
    [
        (["-w", "status", "--json"], True, ("status", "--json")),
        (["--workflows", "status"], True, ("status",)),
        (["-v", "-w", "doctor"], True, ("-v", "doctor")),
        (["-vw", "doctor"], True, ("-v", "doctor")),
        (["-wq", "doctor"], True, ("-q", "doctor")),
        (["-vvw", "doctor"], True, ("-vv", "doctor")),
        (["-ww", "doctor"], True, ("doctor",)),
        (["--log-level", "DEBUG", "-w", "status"], True, ("--log-level", "DEBUG", "status")),
        # A value that looks like the flag is a value, not the flag.
        (["--log-file", "-w", "status"], False, ("--log-file", "-w", "status")),
        # After the command, -w is the command's own.
        (["status", "-w"], False, ("status", "-w")),
        (["-v", "status"], False, ("-v", "status")),
        (["--", "-w"], False, ("--", "-w")),
        (["-", "-w"], False, ("-", "-w")),
        (["-w"], True, ()),
        ([], False, ()),
    ],
)
def test_the_flag_is_read_only_among_the_leading_global_options(
    argv: list[str], remote: bool, forwarded: tuple[str, ...]
) -> None:
    assert WORKFLOWS_INVOCATION.split(argv) == (remote, forwarded)


def test_a_command_carries_its_run_name() -> None:
    command = RemoteCommand(("status", "--json"), ID)
    assert command.run_name == f"vibey {ID}"
    assert RemoteCommand.run_name_for(ID) == f"vibey {ID}"


@pytest.mark.parametrize(
    ("argv", "request_id", "why"),
    [
        ((), ID, "name a command"),
        (("status", "-w"), ID, "cannot itself carry -w"),
        (("--workflows",), ID, "cannot itself carry -w"),
        (("status", "a\x00b"), ID, "NUL"),
        (("x" * RemoteCommand.MAX_CHARS,), ID, "at most"),
        (("status",), "short", "not a request id"),
        (("status",), "-leading-dash-id", "not a request id"),
        (("status",), "has space in it", "not a request id"),
    ],
)
def test_what_cannot_be_sent_is_refused(argv: tuple[str, ...], request_id: str, why: str) -> None:
    with pytest.raises(RemoteCommandRefused, match=why):
        RemoteCommand(argv, request_id)


def test_a_status_is_finished_only_once_done_or_failed() -> None:
    assert not RemoteStatus(ID, RemoteState.QUEUED).finished
    assert not RemoteStatus(ID, RemoteState.RUNNING).finished
    assert RemoteStatus(ID, RemoteState.DONE, exit_code=0).finished
    assert RemoteStatus(ID, RemoteState.FAILED).finished


def test_a_status_reads_as_plain_data() -> None:
    status = RemoteStatus(ID, RemoteState.DONE, url="u", exit_code=3, stdout="o", stderr="e")
    assert status.as_dict() == {
        "request_id": ID,
        "state": "done",
        "url": "u",
        "exit_code": 3,
        "stdout": "o",
        "stderr": "e",
        "detail": "",
    }
