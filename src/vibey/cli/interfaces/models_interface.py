# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey models`.

Mirrors `vibey/cli/models.py` (ADR-0016). Interfaces declare; they never consume. The report
the seams are declared over is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.cli.models import ModelsReport


@runtime_checkable
class ModelsPresenterInterface(Protocol):
    def lines(self, report: ModelsReport) -> list[str]:
        """The families, then what the Ollama here has and says each can do."""
        ...

    def json(self, report: ModelsReport) -> str:
        """The same facts as JSON."""
        ...


@runtime_checkable
class ModelsCommandInterface(Protocol):
    def run(self, *, as_json: bool) -> None: ...

    def report(self) -> ModelsReport:
        """The report `run` prints."""
        ...
