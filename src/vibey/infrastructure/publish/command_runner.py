# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs `git` and `gh` for publishing, with the environment they need and no more.

The environment is the system basics (`SYSTEM_ENVIRONMENT`) plus `SSH_AUTH_SOCK`, so an ssh
remote can use the operator's agent. A token never goes through it: `GH_TOKEN` and
`GITHUB_TOKEN` are forbidden names for every child process, so `gh` must be logged in
(`gh auth login`), as it is on a developer machine. Nothing prompts: a push that would ask
for a password fails instead of hanging the worker.
"""

import asyncio
from pathlib import Path
from typing import Final

from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT, ChildEnvironment
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface

DEFAULT_TIMEOUT_SECONDS: Final = 180.0

_OVERLAY: Final = {
    "GIT_TERMINAL_PROMPT": "0",
    "GH_PROMPT_DISABLED": "1",
    "GH_NO_UPDATE_NOTIFIER": "1",
    "GH_SPINNER_DISABLED": "1",
    "NO_COLOR": "1",
}


class ProgramRunner:
    """Declared by `interfaces/command_runner_interface.py`."""

    __slots__ = ("_environment", "_timeout")

    def __init__(
        self,
        environment: ChildEnvironmentInterface | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._environment = (
            ChildEnvironment(SYSTEM_ENVIRONMENT.extended(["SSH_AUTH_SOCK"]), overlay=_OVERLAY)
            if environment is None
            else environment
        )
        self._timeout = timeout

    async def run(self, argv: tuple[str, ...], *, cwd: Path | None = None) -> CommandResult:
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=cwd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._environment.build(),
            )
        except FileNotFoundError:
            return CommandResult(127, "", f"{argv[0]}: command not found")
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), self._timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            return CommandResult(124, "", f"timed out after {self._timeout:g}s")
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        return CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())
