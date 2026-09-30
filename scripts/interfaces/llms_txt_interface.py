# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/llms_txt.py` implements. Interfaces declare; they never consume.

A *page describer* reads one documentation page and says, in one sentence, what it holds.
A *link source* yields the entries of one part of the index. A *renderer* turns the
entries into the text of `llms.txt`, in the shape https://llmstxt.org describes.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol


class PageDescriberInterface(Protocol):
    """Says what one Markdown page holds, in one plain sentence."""

    def describe(self, path: Path) -> str:
        """The page's declared description, or its first prose sentence; "" when neither."""
        ...


class LinkSourceInterface(Protocol):
    """Yields the index entries of one part of the documentation."""

    def entries(self) -> Sequence[Any]:
        """Each entry carries a section, a title, an absolute URL and a description."""
        ...


class LlmsTxtRendererInterface(Protocol):
    """Writes the entries as the text of an llms.txt file."""

    def render(self, entries: Sequence[Any]) -> str:
        """The whole file: title, summary, then one section per group, in first-seen order."""
        ...
