# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the `vibey --help` command list.

Mirrors `vibey/cli/help_layout.py` (ADR-0016). Interfaces declare; they never consume. The
Typer type the seam is declared over is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import typer


@runtime_checkable
class HelpLayoutInterface(Protocol):
    """Lays the root command list out by what a person came to do."""

    def apply(self, app: typer.Typer) -> None:
        """Group `app`'s commands and sub-apps into titled panels, in the order a newcomer
        needs them, give each a one-line summary, and end the help with worked examples.
        Nothing a command does changes, and its own `--help` keeps its full text."""
        ...

    def unplaced(self, app: typer.Typer) -> list[str]:
        """The names `app` registers that no panel places, so a command added without a
        place in the list is found by a test rather than by a confused user."""
        ...
