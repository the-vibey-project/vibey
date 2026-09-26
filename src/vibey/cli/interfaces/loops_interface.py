# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey loops`.

Mirrors `vibey/cli/loops.py` (ADR-0016). Interfaces declare; they never consume. The report
the seams are declared over is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import LoopsReport


@runtime_checkable
class LoopsPresenterInterface(Protocol):
    """Renders the two loops: for a person first, a program second."""

    def lines(self, report: LoopsReport) -> list[str]:
        """A short plain table per loop: its engines, what each effort passes, the price
        per million tokens, and how to switch a local engine on."""
        ...

    def json(self, report: LoopsReport) -> str:
        """The whole report as the JSON document the VS Code extension reads."""
        ...


@runtime_checkable
class LoopsCommandInterface(Protocol):
    """Runs `vibey loops`, with no database and no network."""

    def run(self, *, as_json: bool) -> None: ...

    def report(self) -> LoopsReport:
        """The report `run` prints; the hub's loops route returns it too."""
        ...
