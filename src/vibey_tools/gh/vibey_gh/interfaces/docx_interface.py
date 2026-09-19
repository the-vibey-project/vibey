# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The dependency-free DOCX seams used by the paper and book exporters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

DocxBlock = Mapping[str, object]


@runtime_checkable
class DocxErrorInterface(Protocol):
    """The actionable exception surface exposed by the DOCX writer."""

    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class DocxWriterInterface(Protocol):
    """Builds a small, portable Word document from semantic document blocks."""

    def build(
        self,
        *,
        title: str,
        author: str,
        blocks: Sequence[DocxBlock],
        page_width_twips: int = 12240,
        page_height_twips: int = 15840,
    ) -> bytes:
        """Return an OOXML package without requiring python-docx at runtime."""

    def write(
        self,
        path: Path,
        *,
        title: str,
        author: str,
        blocks: Sequence[DocxBlock],
        page_width_twips: int = 12240,
        page_height_twips: int = 15840,
    ) -> None:
        """Write the OOXML package to ``path``."""


@runtime_checkable
class HtmlToDocxInterface(Protocol):
    """Turns the sanitized HTML body of a book chapter into semantic blocks."""

    def convert(self, body: str, *, leading_title: str = "") -> Sequence[DocxBlock]:
        """Convert headings, prose, lists, code and tables without dropping content."""
