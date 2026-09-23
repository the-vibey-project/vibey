# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/paper_figures.py` implements. Interfaces declare; they never consume.

A *figure source* reads one tracked record into plain data. A *figure atlas* turns those
readings into the paper's generated figure blocks and writes them between their markers.
"""

from typing import Any, Protocol


class FigureSourceInterface(Protocol):
    """Reads one tracked record (a file, a table, or the git history at a revision)."""

    def load(self) -> dict[str, Any]:
        """The record as plain data: lists, dicts, numbers and strings only."""
        ...


class PaperFigureAtlasInterface(Protocol):
    """Composes the sources into the paper's generated figure blocks."""

    def figures(self, skip: frozenset[str] = frozenset()) -> dict[str, str]:
        """Every generated figure, keyed by its block name, as a ```latex fence."""
        ...

    def apply(self, markdown: str) -> str:
        """`markdown` with every generated block replaced by its regenerated form."""
        ...

    def drift(self, markdown: str, skip: frozenset[str] = frozenset()) -> list[str]:
        """The names of the blocks in `markdown` that regeneration would change."""
        ...
