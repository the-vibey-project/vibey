# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/paper_publishability.py` implements. Interfaces declare; they never consume.

A *paper reader* reads the paper's Markdown into its title, sections, paragraphs and
sentences, each with the line it starts on. A *citation reader* reads the repository's
`CITATION.cff` into the names, titles and keys the checks ask about. A *check* judges one
publishability criterion against both and returns one row per thing it has to say. A
*renderer* writes the rows, and the reviewer's rubric beside them, as text or as JSON.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class PaperReaderInterface(Protocol):
    """Reads the paper's Markdown source, keeping every line number."""

    lines: Sequence[str]

    def title(self) -> str | None:
        """The text of the first `# ` heading, or None when the paper has none."""
        ...

    def paragraphs(self) -> Sequence[Any]:
        """Every block of consecutive non-blank lines, each with its first line's number."""
        ...

    def opening_with(self, marker: str) -> Any | None:
        """The first paragraph whose text begins with `marker`, or None."""
        ...

    def section(self, heading: str) -> Any | None:
        """The `## ` section whose heading line is exactly `heading`, or None."""
        ...

    def subsections(self, section: Any) -> Sequence[Any]:
        """The `### ` subsections inside `section`, each with its heading, body and line."""
        ...

    def bullets(self, section: Any) -> Sequence[Any]:
        """The `- ` list items inside `section`, continuation lines folded in."""
        ...

    def sentences(self, paragraph: Any) -> Sequence[Any]:
        """The sentences of one paragraph, each with the line it starts on."""
        ...


class CitationReaderInterface(Protocol):
    """Reads the Citation File Format record the repository publishes."""

    def author_names(self) -> Sequence[tuple[str, str]]:
        """`(where, name)` for every author named at the top level or under the preferred
        citation; `where` is the key path the author sits under."""
        ...

    def preferred_title(self) -> str | None:
        """`preferred-citation.title`, or None when the record declares no such thing."""
        ...

    def has_key(self, key: str) -> bool:
        """Whether a mapping anywhere in the record carries `key`."""
        ...


class CheckInterface(Protocol):
    """One publishability criterion, judged mechanically."""

    name: str
    required: bool
    reason: str

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> Sequence[Any]:
        """One row per thing to report: a single PASS, or one row per failure found."""
        ...


class ReportRendererInterface(Protocol):
    """Writes an evaluation for a person or for a machine."""

    def text(self, evaluation: Any) -> str:
        """The table of rows, the reason for each check, and the reviewer's rubric."""
        ...

    def json(self, evaluation: Any) -> str:
        """The same evaluation as one JSON document."""
        ...
