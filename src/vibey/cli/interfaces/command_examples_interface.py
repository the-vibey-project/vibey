# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the worked examples that end a command's `--help` (ADR-0016).

Mirrors `vibey/cli/command_examples.py`. Interfaces declare; they never consume. The Typer type
the seam is declared over is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import typer


@runtime_checkable
class CommandExamplesInterface(Protocol):
    """Ends chosen commands' `--help` with examples, and checks that they still parse."""

    def apply(self, app: typer.Typer) -> None:
        """Set each named command's epilog to its examples. Nothing a command does changes,
        and the root help's own epilog is left alone."""
        ...

    def problems(self, app: typer.Typer) -> list[str]:
        """What is wrong with the examples: a command that does not exist, an example its own
        command's parser refuses (a renamed flag, a missing argument), more than two for one
        command, or a required command with none. Empty when every example still holds."""
        ...
