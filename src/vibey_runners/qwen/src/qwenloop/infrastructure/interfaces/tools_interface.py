# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the tools a run's model may call, confined to one worktree."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from qwenloop.application.interfaces import ToolExecutor
from qwenloop.domain.config import ToolLimits


@runtime_checkable
class ShellEnvironmentInterface(Protocol):
    """What a model-chosen shell command may see: an allow-list, never a copy."""

    def admits(self, name: str) -> bool:
        """Whether `name` may reach the command: allowed, and not forbidden."""
        ...

    def build(self) -> dict[str, str]:
        """The allow-listed environment, read from the source at call time."""
        ...


@runtime_checkable
class SandboxToolsInterface(ToolExecutor, Protocol):
    """Runs one named tool call inside `worktree` and answers with a JSON-able mapping.

    A failure the model can correct is an `error` entry, never an exception; a path that
    resolves outside `worktree` is refused. An unknown name is answered with the names
    that do exist, so a model that guessed wrong can correct itself on its next turn.
    """

    @property
    def worktree(self) -> Path:
        """The resolved directory every path argument is confined to."""
        ...

    @property
    def allow_network(self) -> bool:
        """Whether a shell command is run without the network-disabled marker."""
        ...

    @property
    def limits(self) -> ToolLimits:
        """How much one call may read or return."""
        ...

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Every tool name `execute` dispatches, in the order the model is told them."""
        ...
