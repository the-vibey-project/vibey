# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `gh` adapter `vibey -w` runs through: what it asks GitHub, and what it reads back."""

import asyncio
import json
import os
import stat
from pathlib import Path

import pytest

from vibey.application.interfaces import RemoteWorkflowForge
from vibey.domain.remote_command import RemoteCommand, RemoteReport, WorkflowRun
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.workflows.gh_workflows import (
    GH_CLI_ENV_ALLOW,
    GhCliSubprocessExecutor,
    GhRemoteWorkflowForge,
    GhWorkflowsError,
    RemoteWorkflowsSettings,
    RemoteWorkflowsSettingsLoader,
)
from vibey.infrastructure.workflows.interfaces import (
    GhCliExecutorInterface,
    RemoteWorkflowsSettingsInterface,
    RemoteWorkflowsSettingsLoaderInterface,
)

ID = "0123456789abcdef"


class Recorder:
    """Answers each `gh` call from a script, recording the argv it was given."""

    def __init__(self, *answers: CommandResult, files: dict[str, str] | None = None) -> None:
        self.answers = list(answers)
        self.files = files or {}
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        if "download" in argv and self.files:
            target = Path(argv[argv.index("--dir") + 1])
            for name, text in self.files.items():
                (target / name).write_text(text)
        return self.answers.pop(0)


def ok(stdout: str = "") -> CommandResult:
    return CommandResult(0, stdout, "")


def forge(recorder: Recorder, **settings: object) -> GhRemoteWorkflowForge:
    return GhRemoteWorkflowForge(RemoteWorkflowsSettings(**settings), executor=recorder)  # type: ignore[arg-type]


def test_each_satisfies_its_interface() -> None:
    assert isinstance(GhCliSubprocessExecutor(), GhCliExecutorInterface)
    assert isinstance(RemoteWorkflowsSettings(), RemoteWorkflowsSettingsInterface)
    assert isinstance(RemoteWorkflowsSettingsLoader(), RemoteWorkflowsSettingsLoaderInterface)
    assert isinstance(forge(Recorder()), RemoteWorkflowForge)
    assert isinstance(
        GhRemoteWorkflowForge(RemoteWorkflowsSettings())._executor, GhCliSubprocessExecutor
    )


def test_the_settings_have_declared_defaults_and_read_the_environment() -> None:
    loader = RemoteWorkflowsSettingsLoader()
    assert loader.load({}) == RemoteWorkflowsSettings()
    assert RemoteWorkflowsSettings().repo_args() == ()
    loaded = loader.load(
        {
            "VIBEY_WORKFLOWS_REPOSITORY": " o/r ",
            "VIBEY_WORKFLOWS_WORKFLOW": "x.yml",
            "VIBEY_WORKFLOWS_REF": "develop",
            "VIBEY_WORKFLOWS_POLL_SECONDS": "2.5",
            "VIBEY_WORKFLOWS_TIMEOUT_SECONDS": "60",
        }
    )
    assert loaded == RemoteWorkflowsSettings("o/r", "x.yml", "develop", 2.5, 60.0)
    assert loaded.repo_args() == ("--repo", "o/r")
    assert loader.load({"VIBEY_WORKFLOWS_WORKFLOW": "  "}).workflow == "vibey-remote.yml"


@pytest.mark.parametrize(
    ("value", "why"), [("soon", "a number of seconds"), ("0", "positive"), ("-3", "positive")]
)
def test_a_wait_that_is_not_a_positive_number_is_refused(value: str, why: str) -> None:
    with pytest.raises(ValueError, match=f"VIBEY_WORKFLOWS_POLL_SECONDS must be {why}"):
        RemoteWorkflowsSettingsLoader().load({"VIBEY_WORKFLOWS_POLL_SECONDS": value})


async def test_dispatch_sends_the_command_line_as_json_and_the_id() -> None:
    recorder = Recorder(ok())
    await forge(recorder, repository="o/r", ref="develop").dispatch(
        RemoteCommand(("status", "--json", "a b"), ID)
    )
    assert recorder.calls == [
        (
            "gh", "workflow", "run", "vibey-remote.yml", "--repo", "o/r", "--ref", "develop",
            "-f", f"request={ID}", "-f", 'argv=["status", "--json", "a b"]',
        )
    ]  # fmt: skip


async def test_dispatch_without_repository_or_ref_lets_gh_choose() -> None:
    recorder = Recorder(ok())
    await forge(recorder).dispatch(RemoteCommand(("doctor",), ID))
    assert "--repo" not in recorder.calls[0] and "--ref" not in recorder.calls[0]


async def test_a_refused_dispatch_says_why() -> None:
    with pytest.raises(GhWorkflowsError, match="refused to run vibey-remote.yml: HTTP 403"):
        await forge(Recorder(CommandResult(1, "", "HTTP 403\n"))).dispatch(
            RemoteCommand(("doctor",), ID)
        )
    with pytest.raises(GhWorkflowsError, match="no reason given"):
        await forge(Recorder(CommandResult(1, "", ""))).dispatch(RemoteCommand(("doctor",), ID))


async def test_find_reads_the_run_carrying_the_name() -> None:
    runs = [
        {"databaseId": 1, "displayTitle": "vibey other", "status": "completed", "url": "u1"},
        {"databaseId": 2, "displayTitle": f"vibey {ID}", "status": "in_progress", "conclusion": "", "url": "u2"},
    ]  # fmt: skip
    recorder = Recorder(ok(json.dumps(runs)))
    found = await forge(recorder, repository="o/r").find(f"vibey {ID}")
    assert found == WorkflowRun(run_id=2, status="in_progress", conclusion=None, url="u2")
    assert recorder.calls[0][:5] == ("gh", "run", "list", "--workflow", "vibey-remote.yml")
    assert recorder.calls[0][7:9] == ("--event", "workflow_dispatch")


async def test_find_returns_none_until_the_run_shows() -> None:
    assert await forge(Recorder(ok("[]"))).find(f"vibey {ID}") is None
    assert await forge(Recorder(ok(""))).find(f"vibey {ID}") is None


async def test_an_unreadable_listing_raises() -> None:
    with pytest.raises(GhWorkflowsError, match="could not list"):
        await forge(Recorder(CommandResult(4, "", "auth required"))).find("vibey x")


async def test_report_downloads_and_reads_the_artifact() -> None:
    body = json.dumps({"exit_code": 0, "stdout": "ok\n", "stderr": ""})
    recorder = Recorder(ok(), files={"result.json": body})
    assert await forge(recorder).report(7) == RemoteReport(0, "ok\n", "")
    assert recorder.calls[0][:4] == ("gh", "run", "download", "7")
    assert recorder.calls[0][4:6] == ("--name", "vibey-result")


async def test_a_failed_download_or_missing_file_is_no_report() -> None:
    assert await forge(Recorder(CommandResult(1, "", "no artifact"))).report(7) is None
    assert await forge(Recorder(ok())).report(7) is None


@pytest.mark.parametrize(
    "text",
    ["not json", "[1, 2]", '{"exit_code": "0", "stdout": "", "stderr": ""}', '{"exit_code": 0}'],
)
def test_a_report_that_is_not_one_is_none(text: str) -> None:
    assert GhRemoteWorkflowForge.read_report(text) is None


def test_the_gh_environment_is_declared_and_carries_no_vibey_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
        "PGPASSWORD": "secret",
        "ANTHROPIC_API_KEY": "model-key",
        "GH_TOKEN": "ghp_token",
        "GH_CONFIG_DIR": "/home/me/.config/gh",
    }.items():
        monkeypatch.setenv(name, value)
    env = GhCliSubprocessExecutor().environment.build()
    assert "GH_TOKEN" in GH_CLI_ENV_ALLOW
    assert env["GH_TOKEN"] == "ghp_token" and env["GH_CONFIG_DIR"] == "/home/me/.config/gh"
    for secret in ("VIBEY_PG_URL", "PGPASSWORD", "ANTHROPIC_API_KEY"):
        assert secret not in env


async def test_the_gh_executor_runs_gh_only() -> None:
    with pytest.raises(ValueError, match="gh only"):
        await GhCliSubprocessExecutor().execute(("git", "status"))


async def test_a_missing_gh_says_where_to_get_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/nonexistent")
    with pytest.raises(GhWorkflowsError, match="cli.github.com"):
        await GhCliSubprocessExecutor().execute(("gh", "--version"))


async def test_a_real_gh_process_sees_none_of_the_workers_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "gh-env.log"
    fake = tmp_path / "bin" / "gh"
    fake.parent.mkdir()
    fake.write_text(f'#!/bin/sh\nenv | sed "s/=.*//" > "{log}"\necho "[]"\nexit 3\n')
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{fake.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://vibey:secret@db/vibey")
    result = await GhCliSubprocessExecutor().execute(("gh", "run", "list"))
    assert (result.returncode, result.stdout) == (3, "[]\n")
    names = set(log.read_text().split())
    assert "PATH" in names and not {n for n in names if n.startswith(("VIBEY_", "PG"))}


async def test_a_cancelled_gh_call_terminates_and_reaps_its_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        returncode = None
        terminated = False
        waited = False

        async def communicate(self) -> tuple[bytes, bytes]:
            raise asyncio.CancelledError

        def terminate(self) -> None:
            FakeProcess.terminated = True

        async def wait(self) -> int:
            FakeProcess.waited = True
            return -15

    async def spawn(*_argv: str, **_kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(asyncio.CancelledError):
        await GhCliSubprocessExecutor().execute(("gh", "run", "list"))
    assert FakeProcess.terminated and FakeProcess.waited
