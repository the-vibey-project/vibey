# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey -w <command>`: what it prints, what it exits with, and where the flag is read."""

import io
from collections.abc import Mapping, Sequence

import pytest
from typer.testing import CliRunner

from vibey.application.remote_command import RemoteCommandService
from vibey.cli import main as cli_main
from vibey.cli.interfaces.workflows_interface import WorkflowsCommandInterface
from vibey.cli.workflows import TIMED_OUT, WORKFLOWS, WorkflowsCommand
from vibey.domain.remote_command import (
    RemoteCommand,
    RemoteCommandRefused,
    RemoteState,
    RemoteStatus,
)
from vibey.infrastructure.workflows.gh_workflows import GhWorkflowsError

ID = "0123456789abcdef"


class FakeService:
    def __init__(self, status: RemoteStatus | Exception) -> None:
        self.status = status
        self.ran: list[tuple[str, ...]] = []

    async def start(self, argv: Sequence[str]) -> RemoteCommand:  # pragma: no cover - unused
        raise AssertionError

    async def poll(self, request_id: str) -> RemoteStatus:  # pragma: no cover - unused
        raise AssertionError

    async def run(self, argv: Sequence[str]) -> RemoteStatus:
        self.ran.append(tuple(argv))
        if isinstance(self.status, Exception):
            raise self.status
        return self.status


def command(
    status: RemoteStatus | Exception,
) -> tuple[WorkflowsCommand, FakeService, io.StringIO, io.StringIO]:
    service = FakeService(status)
    out, err = io.StringIO(), io.StringIO()
    return (
        WorkflowsCommand(environ={}, service=lambda _env: service, out=out, err=err),
        service,
        out,
        err,
    )


def test_the_command_satisfies_its_interface() -> None:
    assert isinstance(WORKFLOWS, WorkflowsCommandInterface)


def test_a_finished_command_prints_as_it_would_have_and_exits_with_its_code() -> None:
    done = RemoteStatus(
        ID, RemoteState.DONE, url="https://run/7", exit_code=3, stdout="{}\n", stderr="warn\n"
    )
    cmd, service, out, err = command(done)
    assert cmd.run(["status", "--json"]) == 3
    assert service.ran == [("status", "--json")]
    assert out.getvalue() == "{}\n"
    assert err.getvalue() == "vibey -w: ran on GitHub: https://run/7\nwarn\n"


def test_a_run_that_handed_back_nothing_exits_1_and_says_so() -> None:
    cmd, _, out, err = command(
        RemoteStatus(ID, RemoteState.FAILED, url="u", detail="ended `cancelled`")
    )
    assert cmd.run(["doctor"]) == 1
    assert out.getvalue() == "" and err.getvalue().endswith("vibey -w: ended `cancelled`\n")


def test_a_wait_that_ran_out_exits_124() -> None:
    cmd, _, _, err = command(RemoteStatus(ID, RemoteState.QUEUED))
    assert cmd.run(["doctor"]) == TIMED_OUT
    assert err.getvalue() == "vibey -w: queued\n"


@pytest.mark.parametrize(
    ("raised", "code"),
    [
        (RemoteCommandRefused("cannot itself carry -w"), 2),
        (ValueError("VIBEY_WORKFLOWS_POLL_SECONDS must be positive"), 2),
        (GhWorkflowsError("GitHub refused"), 1),
    ],
)
def test_a_refusal_is_said_and_exits_nonzero(raised: Exception, code: int) -> None:
    cmd, _, _, err = command(raised)
    assert cmd.run(["doctor"]) == code
    assert err.getvalue() == f"vibey -w: {raised}\n"


def test_the_default_service_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    service = WorkflowsCommand.default_service({"VIBEY_WORKFLOWS_POLL_SECONDS": "3"})
    assert isinstance(service, RemoteCommandService)
    assert service._poll == 3.0
    seen: list[Mapping[str, str]] = []
    monkeypatch.setenv("VIBEY_WORKFLOWS_REF", "develop")

    def capture(env: Mapping[str, str]) -> FakeService:
        seen.append(env)
        return FakeService(RemoteStatus(ID, RemoteState.DONE, exit_code=0))

    assert WorkflowsCommand(service=capture, out=io.StringIO(), err=io.StringIO()).run(["x"]) == 0
    assert seen[0]["VIBEY_WORKFLOWS_REF"] == "develop"


def test_the_entry_point_sends_a_w_command_line_to_the_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple[str, ...]] = []

    class Recording:
        def run(self, argv: Sequence[str]) -> int:
            sent.append(tuple(argv))
            return 5

    monkeypatch.setattr(cli_main, "WORKFLOWS", Recording())
    with pytest.raises(SystemExit) as exited:
        cli_main.run(["-v", "-w", "status", "--json"])
    assert exited.value.code == 5
    assert sent == [("-v", "status", "--json")]


def test_the_entry_point_runs_everything_else_here(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["vibey", "--version"])
    with pytest.raises(SystemExit) as exited:
        cli_main.run()
    assert exited.value.code == 0
    assert capsys.readouterr().out.startswith("vibey ")


def test_the_flag_reaching_the_parser_is_refused_not_ignored() -> None:
    result = CliRunner().invoke(cli_main.app, ["-w", "status"])
    assert result.exit_code == 2
    assert "read by the `vibey` command itself" in result.output


def test_the_hub_gets_the_same_service_or_says_why_it_is_off(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from vibey.cli.serve import ServeCommand

    assert isinstance(ServeCommand.workflows({}), RemoteCommandService)
    assert ServeCommand.workflows({"VIBEY_WORKFLOWS_TIMEOUT_SECONDS": "never"}) is None
    assert "workflows: off (VIBEY_WORKFLOWS_TIMEOUT_SECONDS must be" in capsys.readouterr().err


def test_every_read_command_and_safe_option_the_hub_names_exists_on_the_cli() -> None:
    """The allowlist names real commands and real options: a renamed command or flag fails
    here instead of silently widening or narrowing what `view` may run (ADR-0085)."""
    import typer

    from vibey.domain.hub_scope import COMMAND_ACTIONS, READ_COMMANDS, RESERVED_COMMANDS

    root = typer.main.get_command(cli_main.app)

    def command(words: tuple[str, ...]) -> object:
        found: object = root
        for word in words:
            found = found.commands[word]  # type: ignore[attr-defined]
        return found

    for words, safe in READ_COMMANDS.items():
        if not words:
            continue
        params = command(words).params  # type: ignore[attr-defined]
        options = {
            o for p in params if p.param_type_name == "option" for o in (*p.opts, *p.secondary_opts)
        }
        assert safe <= options, (words, safe - options)
    for words in (*COMMAND_ACTIONS, *RESERVED_COMMANDS):
        if words:
            command(words)
