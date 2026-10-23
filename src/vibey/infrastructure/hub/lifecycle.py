# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Start, pause, resume and unwind a project for a device that holds `run` (ADR-0091).

The hub owns no write of its own (ADR-0067). Each of these is what `vibey new`, `retry`, `recover`
and `abandon` already do, so this runs those, on this host, exactly as a person at its terminal
would, and reads the JSON the CLI prints. It cannot drift from them and cannot route around a
check they make: the checkout hold, the Sabbath, the runtime config's own refusals.

A device never names a path. The host declares `[hub] projects_root`; a project's folder is
`<projects_root>/<name>`, made here, and with no `projects_root` nothing can be started from a
device at all (the default).

Declared by `interfaces/lifecycle_interface.py` and
`application/hub/interfaces/lifecycle_interface.py::ProjectLifecycleInterface`.
"""

import asyncio
import json
import subprocess  # nosec B404 - fixed argv, never shell=True
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from uuid import UUID

from vibey.domain.errors import (
    LifecycleConflict,
    LifecycleFailed,
    LifecycleInvalid,
    LifecycleRefused,
    LifecycleUnavailable,
)
from vibey.infrastructure.hub.interfaces.lifecycle_interface import (
    ProjectFoldersInterface,
    VibeyCommandRunnerInterface,
)
from vibey.infrastructure.worker_launcher import default_executable

COMMAND_SECONDS: Final = 120.0
"""How long one `vibey` command may run before the hub gives up on it."""

EXIT_USAGE: Final = 2
EXIT_HELD: Final = 3
EXIT_RESTING: Final = 75
"""`vibey`'s own exit codes: a usage error, a checkout a live project holds, and the Sabbath."""

SHOWN_CHARS: Final = 600
"""How much of a failed command's own words a device is shown."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    """What one `vibey` command did."""

    code: int
    stdout: str
    stderr: str


class SubprocessVibeyRunner:
    """`VibeyCommandRunnerInterface` through the `vibey` this process is running as."""

    def __init__(
        self,
        *,
        executable: str | None = None,
        run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._executable = executable if executable is not None else default_executable()
        self._run = run

    def run(self, args: Sequence[str]) -> CommandResult:
        try:
            done = self._run(
                [self._executable, *args],  # nosec B603 - fixed argv, never shell=True
                capture_output=True,
                text=True,
                check=False,
                timeout=COMMAND_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                124, "", f"vibey {args[0]} took longer than {COMMAND_SECONDS:.0f}s"
            )
        except OSError as exc:
            return CommandResult(127, "", f"vibey could not be run: {exc}")
        return CommandResult(done.returncode, done.stdout, done.stderr)


class GitProjectFolders:
    """`ProjectFoldersInterface` with git: a folder, a repository, and one empty commit so a
    worktree can be taken from it."""

    def __init__(
        self, *, run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
    ) -> None:
        self._run = run

    def make(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=False)
        for args in (
            ["init", "-q", "-b", "main"],
            [
                "-c",
                "user.name=vibey",
                "-c",
                "user.email=vibey@localhost",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                f"chore: start {path.name}",
            ],
        ):
            done = self._run(
                ["git", "-C", str(path), *args],  # nosec B603 B607 - fixed argv
                capture_output=True,
                text=True,
                check=False,
            )
            if done.returncode != 0:
                raise OSError(f"git {args[0]} failed: {done.stderr.strip()}")


def refusal(command: str, result: CommandResult) -> LifecycleRefused:
    """The refusal a failed `vibey` command is, read from its exit code, in its own words."""
    said = (result.stderr.strip() or result.stdout.strip() or f"vibey {command} failed")[
        :SHOWN_CHARS
    ]
    if result.code == EXIT_RESTING:
        return LifecycleUnavailable(said)
    if result.code in (EXIT_HELD, 1):
        return LifecycleConflict(result.stdout.strip()[:SHOWN_CHARS] or said)
    if result.code == EXIT_USAGE:
        return LifecycleInvalid(said)
    return LifecycleFailed(said)


class CliProjectLifecycle:
    """Runs the audited commands for a device. `projects_root` is where it may make folders;
    with none declared, `create` says so (pausing, resuming and unwinding a project that exists
    need no folder)."""

    UNDECLARED: Final = (
        "this host has not allowed projects to be started from a device: set [hub] "
        "projects_root in vibey.toml on the host to a folder devices may create projects in"
    )

    def __init__(
        self,
        *,
        projects_root: Path | None,
        runner: VibeyCommandRunnerInterface | None = None,
        folders: ProjectFoldersInterface | None = None,
    ) -> None:
        self._root = projects_root
        self._runner = runner if runner is not None else SubprocessVibeyRunner()
        self._folders = folders if folders is not None else GitProjectFolders()

    async def create(self, name: str, intake: str) -> Mapping[str, object]:
        if self._root is None:
            raise LifecycleUnavailable(self.UNDECLARED)
        folder = self._root / name
        try:
            await asyncio.to_thread(self._folders.make, folder)
        except FileExistsError as exc:
            raise LifecycleConflict(
                f"a folder named {name} already exists on the host; choose another name"
            ) from exc
        except OSError as exc:
            raise LifecycleFailed(f"the host could not make the folder: {exc}") from exc
        args = ["new", name, "--repo", str(folder), "--json"]
        if intake:
            args += ["--intake", intake]
        created = await self._json("new", args)
        project_id = created.get("project_id")
        if isinstance(project_id, str):
            # The interview is queued, and nothing runs it until a worker does.
            await self._must("retry", ["retry", project_id, "--keep-workers", "--start-worker"])
        return created

    async def start_work(self, project_id: UUID) -> Mapping[str, object]:
        out = await self._must(
            "retry", ["retry", str(project_id), "--keep-workers", "--start-worker"]
        )
        return {"message": out}

    async def pause_work(self, project_id: UUID) -> Mapping[str, object]:
        out = await self._must(
            "recover", ["recover", "--project", str(project_id), "--stop-workers"]
        )
        return {"message": out}

    async def abandon(
        self, project_id: UUID, reason: str, *, by: str, dry_run: bool
    ) -> Mapping[str, object]:
        args = ["abandon", str(project_id), "--reason", reason, "--by", by, "--json"]
        return await self._json("abandon", args + (["--dry-run"] if dry_run else []))

    async def _must(self, command: str, args: Sequence[str]) -> str:
        result = await asyncio.to_thread(self._runner.run, args)
        if result.code != 0:
            raise refusal(command, result)
        return result.stdout.strip()

    async def _json(self, command: str, args: Sequence[str]) -> dict[str, Any]:
        out = await self._must(command, args)
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError as exc:
            raise LifecycleFailed(f"vibey {command} did not print JSON") from exc
        if not isinstance(parsed, dict):
            raise LifecycleFailed(f"vibey {command} did not print a JSON object")
        return parsed
