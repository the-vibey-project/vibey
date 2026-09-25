# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey answer`, end to end against real Postgres: a gate is answered once, by the
person who ran the command (or the name they gave), and a retry names its request."""

import asyncio
import os
import pwd
from pathlib import Path
from uuid import UUID

import pytest

from tests.cli.test_projects_and_gates_cli import (
    APPROVAL,
    _an_empty_database,  # noqa: F401 -- the autouse fixture, reused so each test starts empty
    _gate,
    _new_project,
    _raise,
    _run,
)
from vibey.bootstrap import build_app
from vibey.cli.errors import EXIT_BLOCKED
from vibey.domain.ledger import EventKind

pytestmark = pytest.mark.integration

# What `ProcessCaller` records: the operating system's name for this process's uid.
ACCOUNT = pwd.getpwuid(os.getuid()).pw_name


def _open_gate(tmp_path: Path) -> str:
    async def seed() -> str:
        project = await _new_project("greeter", tmp_path)
        return str((await _raise(project.project_id, APPROVAL, with_job=True)).gate_id)

    return asyncio.run(seed())


def _answered_events() -> list[dict[str, object]]:
    return asyncio.run(_events())


async def _events() -> list[dict[str, object]]:
    async with build_app() as resources:
        projects = await resources.projects.list_all()
        events = await resources.ledger.all_for_project(projects[0].project_id)
    return [dict(e.payload) for e in events if e.kind is EventKind.GATE_ANSWERED]


def test_the_account_that_ran_it_is_recorded(tmp_path: Path) -> None:
    gate_id = _open_gate(tmp_path)

    result = _run("answer", gate_id, "--verdict", "accept")

    assert result.exit_code == 0, result.output
    assert result.stdout == f"answered {gate_id} as {ACCOUNT}\n"
    settled = asyncio.run(_gate(UUID(gate_id)))
    assert settled.answered_by == ACCOUNT
    (event,) = _answered_events()
    assert (event["by"], event["account"]) == (ACCOUNT, ACCOUNT)


def test_a_named_answerer_is_recorded_with_the_account_beside_it(tmp_path: Path) -> None:
    gate_id = _open_gate(tmp_path)

    result = _run("answer", gate_id, "--verdict", "accept", "--by", "vibey-vscode")

    assert result.exit_code == 0, result.output
    assert result.stdout == f"answered {gate_id} as vibey-vscode\n"
    (event,) = _answered_events()
    assert (event["by"], event["account"]) == ("vibey-vscode", ACCOUNT)


def test_a_retry_with_its_request_id_is_a_no_op(tmp_path: Path) -> None:
    gate_id = _open_gate(tmp_path)
    first = _run("answer", gate_id, "--verdict", "accept", "--request-id", "ext-1")

    again = _run("answer", gate_id, "--verdict", "accept", "--request-id", "ext-1")

    assert first.exit_code == 0, first.output
    assert again.exit_code == 0, again.output
    assert again.stdout == f"already answered {gate_id} by this request; nothing changed\n"
    assert len(_answered_events()) == 1


def test_a_second_answer_is_refused_and_the_first_stands(tmp_path: Path) -> None:
    gate_id = _open_gate(tmp_path)
    assert _run("answer", gate_id, "--verdict", "accept").exit_code == 0

    refused = _run("answer", gate_id, "--verdict", "changes")

    assert refused.exit_code == EXIT_BLOCKED
    assert f"gate {gate_id} was already answered by" in refused.stderr
    assert "vibey ledger search --kind GateAnswered" in refused.stderr
    settled = asyncio.run(_gate(UUID(gate_id)))
    assert settled.answer == {"verdict": "accept"}


def test_an_unknown_gate_is_a_message_not_a_traceback() -> None:
    missing = "00000000-0000-4000-8000-00000000abcd"

    result = _run("answer", missing, "--verdict", "accept")

    assert result.exit_code == EXIT_BLOCKED
    assert f"Error: no gate {missing}" in result.stderr
    assert "vibey gates" in result.stderr
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    ("flag", "value", "message"),
    [
        ("--by", "\t", "the name a record is made under cannot be empty"),
        ("--request-id", "two words", "a request id cannot contain spaces"),
    ],
)
def test_a_label_or_request_id_that_cannot_be_stored_is_refused(
    tmp_path: Path, flag: str, value: str, message: str
) -> None:
    gate_id = _open_gate(tmp_path)

    result = _run("answer", gate_id, "--verdict", "accept", flag, value)

    assert result.exit_code == EXIT_BLOCKED
    assert message in result.stderr
    assert _answered_events() == []
