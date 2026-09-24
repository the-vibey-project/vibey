# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the executor the `az` CLI adapter runs through.

Mirrors `vibey/infrastructure/azure/az_cli.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from typing import Protocol, runtime_checkable

from vibey.infrastructure.interfaces import CommandExecutor
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface


@runtime_checkable
class AzCliExecutorInterface(CommandExecutor, Protocol):
    """Runs one `az` command with an environment built from its own declaration."""

    @property
    def environment(self) -> ChildEnvironmentInterface:
        """The builder for every `az` child's environment."""
        ...
