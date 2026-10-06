# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams behind `vibey -w`: the forge that runs a command on its workflows, and the
service the CLI and the hub drive it through (ADR-0085). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey.domain.remote_command import RemoteCommand, RemoteReport, RemoteStatus, WorkflowRun


@runtime_checkable
class RemoteWorkflowForge(Protocol):
    """The forge whose GitHub-hosted runners run a vibey command."""

    async def dispatch(self, command: RemoteCommand) -> None:
        """Start the remote-command workflow for `command`. Raises when the forge refuses."""
        ...

    async def find(self, command_run_name: str) -> WorkflowRun | None:
        """The run carrying this name, or None while the forge has not shown it yet."""
        ...

    async def report(self, run_id: int) -> RemoteReport | None:
        """What a finished run handed back, or None when it handed back nothing readable."""
        ...


@runtime_checkable
class RemoteCommandServiceInterface(Protocol):
    """Sends a vibey command to the workflows, and says what it came to. Stateless: a run is
    found again by its request id alone, so any process, or a hub after a restart, can ask."""

    async def start(self, argv: Sequence[str], *, request_id: str | None = None) -> RemoteCommand:
        """Dispatch `argv`; the command, with the request id its run will carry. The caller
        may name the id (the hub mints one bound to its starter); otherwise a fresh one is
        made. Either way it is held to `RemoteCommand.REQUEST_ID`."""
        ...

    async def poll(self, request_id: str) -> RemoteStatus:
        """Where the command with this request id is now."""
        ...

    async def run(self, argv: Sequence[str]) -> RemoteStatus:
        """Dispatch `argv` and wait for it; a status that is not finished when the wait ran
        out says so in its `detail`."""
        ...
