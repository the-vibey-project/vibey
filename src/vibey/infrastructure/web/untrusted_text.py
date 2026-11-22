# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Text from the open web made safe to print: no terminal control in it.

A search result or a fetched page is other people's text. Printed raw, an escape sequence in it
drives the reader's terminal: `ESC ] 52 ; ... BEL` writes the clipboard, `ESC [ 2 J` clears the
screen, `ESC ] 8 ;; ...` hides a link behind other text, and a bidirectional override reorders
what is shown. So before any of it is kept, every escape sequence (CSI, OSC, DCS and the like,
7-bit or 8-bit) is removed whole, and then every remaining control (C0 but tab and newline, DEL,
C1) and format character (bidirectional overrides, zero-width marks) is removed. Words and
punctuation are left exactly as they were. The same cleaned text goes to the terminal and to
`--json`, so the two never disagree.

Declared by `interfaces/untrusted_text_interface.py` (ADR-0016).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

_SEQUENCES: Final = re.compile(
    r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]"  # CSI ... final byte
    r"|(?:\x1b[\]PX^_]|[\x90\x98\x9d\x9e\x9f])[^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)?"  # OSC, DCS...
    r"|\x1b[ -/]*[0-~]?"  # any other escape, with its intermediates and final byte
)
_KEPT: Final = frozenset("\t\n")


class UntrustedText:
    """Declared by `interfaces/untrusted_text_interface.py::UntrustedTextInterface`."""

    @staticmethod
    def clean(text: str) -> str:
        """`text` with every terminal escape sequence and control or format character removed;
        tabs and newlines kept."""
        stripped = _SEQUENCES.sub("", text)
        return "".join(
            char
            for char in stripped
            if char in _KEPT or unicodedata.category(char) not in {"Cc", "Cf"}
        )

    @staticmethod
    def is_clean_url(url: str) -> bool:
        """Whether `url` holds no control, format or space character at all."""
        return not any(char.isspace() or unicodedata.category(char) in {"Cc", "Cf"} for char in url)
