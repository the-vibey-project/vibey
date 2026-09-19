# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seams of the research-paper exporter."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PaperErrorInterface(Protocol):
    """The actionable exception surface exposed by the paper exporter."""

    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class PaperDocumentInterface(Protocol):
    """The parsed paper document consumed by the LaTeX and DOCX renderers."""

    title: str
    abstract: list[str]
    body: list[str]
    bibliography: list[str]
