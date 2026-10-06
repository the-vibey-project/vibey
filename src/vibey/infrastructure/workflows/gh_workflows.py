# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""GhRemoteWorkflowForge: the real `RemoteWorkflowForge`, over the `gh` CLI (ADR-0085).

`vibey -w <command>` dispatches `.github/workflows/vibey-remote.yml` with the command line as
JSON and a request id, finds the run by the name that id gives it, and downloads the report
the run hands back as its `vibey-result` artifact. `gh` must be installed and logged in
(`gh auth login`), or given `GH_TOKEN`; the token needs `actions: write` on the repository to
dispatch and `actions: read` to follow.

`gh` runs with an environment built from its own declaration, never copied from vibey's:
the worker's database DSN and engine keys never reach a child that talks to the forge.
"""

import asyncio
import json
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Final

from vibey.application.interfaces.remote_command import RemoteWorkflowForge
from vibey.domain.errors import VibeyError
from vibey.domain.remote_command import RemoteCommand, RemoteReport, WorkflowRun
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.interfaces import CommandExecutor
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT, ChildEnvironment
from vibey.infrastructure.workflows.interfaces import (
    GhCliExecutorInterface,
    RemoteWorkflowsSettingsInterface,
    RemoteWorkflowsSettingsLoaderInterface,
)

#: What `gh` reads of its environment beyond the system basics: its login, its host and
#: its own configuration. Nothing of vibey's.
GH_CLI_ENV_ALLOW: Final[tuple[str, ...]] = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
    "GH_HOST",
    "GH_CONFIG_DIR",
    "GH_PROMPT_DISABLED",
)

#: The artifact the workflow hands its report back in, and the file inside it.
RESULT_ARTIFACT: Final[str] = "vibey-result"
RESULT_FILE: Final[str] = "result.json"

#: How many recent dispatched runs are searched for a request's name.
FIND_LIMIT: Final[int] = 50


class GhWorkflowsError(VibeyError):
    """`gh` refused a dispatch, or could not be run at all."""


class GhCliSubprocessExecutor(GhCliExecutorInterface):
    """Runs one `gh` command with an environment built from its own declaration. Declared
    by `interfaces/gh_workflows_interface.py::GhCliExecutorInterface`."""

    __slots__ = ("_environment",)

    def __init__(self, *, env_allow: Iterable[str] = ()) -> None:
        self._environment = ChildEnvironment(
            SYSTEM_ENVIRONMENT.extended((*GH_CLI_ENV_ALLOW, *env_allow), where="gh CLI environment")
        )

    @property
    def environment(self) -> ChildEnvironment:
        return self._environment

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        if not argv or PurePath(argv[0]).name != "gh":
            raise ValueError(f"the gh executor runs gh only, not {argv[:1]!r}")
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._environment.build(),
            )
        except FileNotFoundError as missing:
            raise GhWorkflowsError(
                "vibey -w needs the GitHub CLI (`gh`) on PATH: https://cli.github.com"
            ) from missing
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        return CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())


@dataclass(frozen=True)
class RemoteWorkflowsSettings(RemoteWorkflowsSettingsInterface):
    """Where `vibey -w` sends a command, and how long it waits. Declared by
    `interfaces/gh_workflows_interface.py::RemoteWorkflowsSettingsInterface`."""

    repository: str = ""
    workflow: str = "vibey-remote.yml"
    ref: str = ""
    poll_seconds: float = 10.0
    timeout_seconds: float = 3600.0

    def repo_args(self) -> tuple[str, ...]:
        return ("--repo", self.repository) if self.repository else ()


class RemoteWorkflowsSettingsLoader(RemoteWorkflowsSettingsLoaderInterface):
    """Reads `VIBEY_WORKFLOWS_*`, each with the default `RemoteWorkflowsSettings` declares.

    `VIBEY_WORKFLOWS_REPOSITORY` (OWNER/NAME; empty: the working directory's git remote),
    `VIBEY_WORKFLOWS_WORKFLOW`, `VIBEY_WORKFLOWS_REF` (empty: the repository's default
    branch), `VIBEY_WORKFLOWS_POLL_SECONDS` and `VIBEY_WORKFLOWS_TIMEOUT_SECONDS`."""

    PREFIX: Final[str] = "VIBEY_WORKFLOWS_"

    def load(self, environ: Mapping[str, str]) -> RemoteWorkflowsSettings:
        defaults = RemoteWorkflowsSettings()

        def text(name: str, default: str) -> str:
            return environ.get(self.PREFIX + name, default).strip()

        def seconds(name: str, default: float) -> float:
            raw = text(name, "")
            if not raw:
                return default
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(f"{self.PREFIX}{name} must be a number of seconds") from None
            if value <= 0:
                raise ValueError(f"{self.PREFIX}{name} must be positive")
            return value

        return RemoteWorkflowsSettings(
            repository=text("REPOSITORY", defaults.repository),
            workflow=text("WORKFLOW", defaults.workflow) or defaults.workflow,
            ref=text("REF", defaults.ref),
            poll_seconds=seconds("POLL_SECONDS", defaults.poll_seconds),
            timeout_seconds=seconds("TIMEOUT_SECONDS", defaults.timeout_seconds),
        )


class GhRemoteWorkflowForge(RemoteWorkflowForge):
    """Implements `application/interfaces/remote_command.py::RemoteWorkflowForge` over `gh`."""

    def __init__(
        self,
        settings: RemoteWorkflowsSettingsInterface,
        *,
        executor: CommandExecutor | None = None,
        gh: str = "gh",
    ) -> None:
        self._settings = settings
        self._executor: CommandExecutor = executor or GhCliSubprocessExecutor()
        self._gh = gh

    async def dispatch(self, command: RemoteCommand) -> None:
        argv = (
            self._gh,
            "workflow",
            "run",
            self._settings.workflow,
            *self._settings.repo_args(),
            *(("--ref", self._settings.ref) if self._settings.ref else ()),
            "-f",
            f"request={command.request_id}",
            "-f",
            f"argv={json.dumps(list(command.argv))}",
        )
        result = await self._executor.execute(argv)
        if result.returncode:
            raise GhWorkflowsError(
                f"GitHub refused to run {self._settings.workflow}: "
                + (result.stderr.strip() or result.stdout.strip() or "no reason given")[:500]
            )

    async def find(self, command_run_name: str) -> WorkflowRun | None:
        result = await self._executor.execute(
            (
                self._gh,
                "run",
                "list",
                "--workflow",
                self._settings.workflow,
                *self._settings.repo_args(),
                "--event",
                "workflow_dispatch",
                "--limit",
                str(FIND_LIMIT),
                "--json",
                "databaseId,displayTitle,status,conclusion,url",
            )
        )
        if result.returncode:
            raise GhWorkflowsError(
                "could not list the workflow's runs: " + result.stderr.strip()[:500]
            )
        for run in json.loads(result.stdout or "[]"):
            if run.get("displayTitle") == command_run_name:
                return WorkflowRun(
                    run_id=int(run["databaseId"]),
                    status=str(run.get("status", "")),
                    conclusion=run.get("conclusion") or None,
                    url=str(run.get("url", "")),
                )
        return None

    async def report(self, run_id: int) -> RemoteReport | None:
        with tempfile.TemporaryDirectory(prefix="vibey-remote-") as scratch:
            result = await self._executor.execute(
                (
                    self._gh,
                    "run",
                    "download",
                    str(run_id),
                    *self._settings.repo_args(),
                    "--name",
                    RESULT_ARTIFACT,
                    "--dir",
                    scratch,
                )
            )
            path = Path(scratch) / RESULT_FILE
            if result.returncode or not path.is_file():
                return None
            return self.read_report(path.read_text(encoding="utf-8"))

    @staticmethod
    def read_report(text: str) -> RemoteReport | None:
        """The report a run handed back, or None when it is not one (10.f: a report that
        cannot be read is never taken for the command having run)."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        code, out, err = data.get("exit_code"), data.get("stdout"), data.get("stderr")
        if not isinstance(code, int) or not isinstance(out, str) or not isinstance(err, str):
            return None
        return RemoteReport(exit_code=code, stdout=out, stderr=err)
