# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind a vibey command run on the workflows.

Mirrors `vibey/domain/remote_command.py` (ADR-0016, ADR-0085). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class RemoteCommandInterface(Protocol):
    """One command line for the workflows, and the id its run is found by."""

    argv: tuple[str, ...]
    request_id: str

    @property
    def run_name(self) -> str:
        """The name the run carries on the forge."""
        ...

    @classmethod
    def run_name_for(cls, request_id: str) -> str:
        """The run name a request id gives; refuses anything that is not a request id."""
        ...


@runtime_checkable
class WorkflowsInvocationInterface(Protocol):
    """Reads `-w`/`--workflows` out of vibey's leading global options."""

    def split(self, argv: Sequence[str]) -> tuple[bool, tuple[str, ...]]:
        """Whether the command line asks for the workflows, and the command line without
        the flag."""
        ...
