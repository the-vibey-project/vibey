# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey -w <command>` / `vibey --workflows <command>`: run it on GitHub's runners (ADR-0085).

The flag is read by the `vibey` entry point before the command line is parsed (`main.run`),
because it changes where every command runs, not what one command does: the command line,
without the flag, goes to `.github/workflows/vibey-remote.yml`, which runs it with vibey on a
GitHub-hosted runner and hands back what it printed and its exit code. This prints them as
the command would have, so `vibey -w status --json | jq` reads the same as `vibey status
--json | jq`. Where it ran is said on stderr.

Settings are the environment's (`VIBEY_WORKFLOWS_*`, `RemoteWorkflowsSettingsLoader`): which
repository, which workflow, which branch, how often to look and how long to wait.
"""

import asyncio
import os
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Final, TextIO

from vibey.application.interfaces.remote_command import RemoteCommandServiceInterface
from vibey.application.remote_command import RemoteCommandService
from vibey.cli.interfaces.workflows_interface import WorkflowsCommandInterface
from vibey.domain.remote_command import RemoteCommandRefused, RemoteState
from vibey.infrastructure.workflows.gh_workflows import (
    GhRemoteWorkflowForge,
    GhWorkflowsError,
    RemoteWorkflowsSettingsLoader,
)

#: The exit code for a wait that ran out, as `timeout(1)` uses it.
TIMED_OUT: Final[int] = 124


class WorkflowsCommand(WorkflowsCommandInterface):
    """Implements `WorkflowsCommandInterface`. Declared by
    `interfaces/workflows_interface.py`."""

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        service: Callable[[Mapping[str, str]], RemoteCommandServiceInterface] | None = None,
        out: TextIO | None = None,
        err: TextIO | None = None,
    ) -> None:
        self._environ = environ
        self._service = service or self.default_service
        self._out = out
        self._err = err

    @staticmethod
    def default_service(environ: Mapping[str, str]) -> RemoteCommandServiceInterface:
        settings = RemoteWorkflowsSettingsLoader().load(environ)
        return RemoteCommandService(
            GhRemoteWorkflowForge(settings),
            new_id=lambda: uuid.uuid4().hex,
            sleep=asyncio.sleep,
            poll_seconds=settings.poll_seconds,
            timeout_seconds=settings.timeout_seconds,
        )

    def run(self, argv: Sequence[str]) -> int:
        out = self._out or sys.stdout
        err = self._err or sys.stderr
        try:
            service = self._service(self._environ if self._environ is not None else os.environ)
            status = asyncio.run(service.run(argv))
        except (RemoteCommandRefused, ValueError) as refused:
            print(f"vibey -w: {refused}", file=err)
            return 2
        except GhWorkflowsError as failed:
            print(f"vibey -w: {failed}", file=err)
            return 1
        if status.url:
            print(f"vibey -w: ran on GitHub: {status.url}", file=err)
        if status.state is RemoteState.DONE and status.exit_code is not None:
            out.write(status.stdout)
            err.write(status.stderr)
            return status.exit_code
        print(f"vibey -w: {status.detail or status.state.value}", file=err)
        return TIMED_OUT if not status.finished else 1


WORKFLOWS: Final[WorkflowsCommandInterface] = WorkflowsCommand()
"""What `vibey -w` runs. Annotated with the interface so `mypy --strict` checks the class
against its declared seam."""
