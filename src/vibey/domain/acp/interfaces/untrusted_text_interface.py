# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/untrusted_text.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class UntrustedTextInterface(Protocol):
    """Hub and ledger text made safe to show: whole characters, cut, no autolinks, no Markdown."""

    def line(self, value: Any, *, limit: int) -> str:
        """One line, safe at the start of a line: at most `limit` characters as written (then
        "..."), defanged and escaped, leading spaces dropped and a leading marker escaped."""
        ...

    def block(self, value: Any, *, limit: int) -> str:
        """Like `line`, but each line break kept as a hard break (a blank line as a paragraph
        break), so text written in lines -- the hub chat's reply -- shows as plain text."""
        ...

    def code(self, value: Any, *, limit: int) -> str:
        """A tool's result as a fenced code block: cut to `limit` characters (then "..."),
        non-printable characters made spaces, lines and indentation kept, and a fence longer
        than any run of backticks inside, so nothing in it renders or links."""
        ...

    def render(self, segments: Sequence[tuple[str, bool]], limit: int) -> str:
        """The segments joined and cut to `limit` characters as written (then "..."), each one
        marked untrusted defanged and escaped after the cut. For spans in the middle of a line
        whose other parts vibey wrote."""
        ...

    def escape(self, text: str) -> str:
        """`text` defanged and escaped, with no cut and nothing else changed."""
        ...

    def one_line(self, value: Any) -> str:
        """`value` as text with every non-printable character a space (`None` reads `?`)."""
        ...
