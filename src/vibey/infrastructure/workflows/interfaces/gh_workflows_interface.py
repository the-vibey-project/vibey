# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the `gh` adapter `vibey -w` runs commands through.

Mirrors `vibey/infrastructure/workflows/gh_workflows.py` (ADR-0016, ADR-0085). Interfaces
declare; they never consume.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey.infrastructure.interfaces import CommandExecutor
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface


@runtime_checkable
class GhCliExecutorInterface(CommandExecutor, Protocol):
    """Runs one `gh` command with an environment built from its own declaration."""

    @property
    def environment(self) -> ChildEnvironmentInterface:
        """The builder for every `gh` child's environment."""
        ...


@runtime_checkable
class RemoteWorkflowsSettingsInterface(Protocol):
    """Where `vibey -w` sends a command, and how long it waits."""

    repository: str
    workflow: str
    ref: str
    poll_seconds: float
    timeout_seconds: float

    def repo_args(self) -> tuple[str, ...]:
        """`--repo OWNER/NAME` when one is declared; else nothing, and `gh` reads the
        repository from the working directory's git remote."""
        ...


@runtime_checkable
class RemoteWorkflowsSettingsLoaderInterface(Protocol):
    """Reads the settings from the environment, each with its declared default."""

    def load(self, environ: Mapping[str, str]) -> RemoteWorkflowsSettingsInterface:
        """The settings; raises `ValueError` for a value that is not one."""
        ...
