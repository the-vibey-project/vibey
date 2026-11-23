# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plugin text made safe to put in front of a model or on a terminal (SP-LOOPS Task 6; design
Decision 10).

A skill's description is loaded up front into every loop's context, and a skipped row's reason is
printed to the person, so both are held to one line of visible text: whitespace of any kind (line
and paragraph breaks, tabs, runs of space) becomes one space and the ends are trimmed; every other
control character (C0, C1, DEL, so ESC and the terminal sequences it starts), format character
(bidi overrides and isolates, zero-width characters, a BOM) and lone surrogate (an undecodable byte
in a file name) is removed. Text still longer than the limit is cut and
ends in `ELLIPSIS`, so a cut is never silent. Declared by
`interfaces/safe_text_interface.py::SafeTextInterface`.
"""

from __future__ import annotations

import unicodedata
from typing import Final

ELLIPSIS: Final = "…"
_DROPPED: Final = frozenset({"Cc", "Cf", "Cs"})
"""Controls, format characters and surrogates that are not whitespace: removed outright."""


class SafeText:
    """Declared by `interfaces/safe_text_interface.py::SafeTextInterface`."""

    def clean(self, text: str, limit: int) -> str:
        if limit < 1:
            raise ValueError(f"a text limit must be at least 1, not {limit}")
        kept: list[str] = []
        for char in text:
            if char.isspace():  # a line break, tab or separator breaks text: one space
                kept.append(" ")
            elif unicodedata.category(char) not in _DROPPED:
                kept.append(char)
        line = " ".join("".join(kept).split())
        if len(line) <= limit:
            return line
        return line[: limit - 1].rstrip() + ELLIPSIS
