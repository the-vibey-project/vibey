# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for finding a Markdown fenced code block that never closes (vibey ADR-0016)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class UnclosedFence:
    """A fence that opened and was still open at the end of the document.

    `line` is 1-based; `marker` is the opening run exactly as written (three or more
    backticks or tildes), which is what a closing fence has to match.
    """

    line: int
    marker: str


@runtime_checkable
class MarkdownFencesInterface(Protocol):
    """Reads Markdown the way CommonMark does, as far as fenced code blocks go.

    The documentation deep scan used to count every ```` ``` ```` in a file and call an odd
    total an unclosed block. A fence written inside an inline code span, inside a regex in
    a fenced Python block, or as a four-backtick fence around a three-backtick example is
    not a fence delimiter at all, so the count failed a file every CommonMark parser
    renders correctly -- every day from 2026-09-28.
    """

    def unclosed(self, text: str) -> UnclosedFence | None:
        """The fence that runs to the end of `text`, or `None` when every fence closes.

        A fence closes only on a line holding nothing but a run of the same character, at
        least as long as the opener, indented at most three columns past its container. A
        fence inside a list item or a block quote also ends where that container ends;
        that is CommonMark, not an error, and is not reported.
        """
        ...
