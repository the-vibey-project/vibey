# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plugin text made safe to put in front of a model or on a terminal (SP-LOOPS Task 6; design
Decision 10; the automated security review's findings on invisible characters).

A skill's description is loaded up front into every loop's context, and a skipped row is printed to
the person, so both are held to one line of characters someone can see. It is an allowlist, not a
denylist: after NFKC normalisation a character is kept only if it is a letter, number, punctuation
or symbol (categories L, N, P, S) and not one of the `INVISIBLE` characters those categories (or
the marks) contain -- Hangul and Braille fillers, variation selectors, the combining grapheme
joiner and the Mongolian free variation selectors. A combining mark (M) is kept only directly after
a visible base character, at most `MAX_MARKS` in a row, so a stack of marks cannot bury the text.
Every kind of whitespace (tabs, line and paragraph breaks, no-break spaces) becomes one space;
everything else -- controls (so ESC and the sequences it starts), format characters (bidi controls,
zero-width characters, tag characters), surrogates, private-use and unassigned code points -- is
removed. The result is normalised again (a removal can let a base and its mark compose), runs of
space collapse and the ends are trimmed; text still longer than the limit is cut and ends in
`ELLIPSIS`, so a cut is never silent. Before any of this the raw text is cut to `RAW_FACTOR` times
the limit (and the result then always ends in `ELLIPSIS`): CPython 3.12's NFKC is quadratic in a
long run of combining marks, so the cost follows the limit, never the input. Each step is one pass
over that bounded text, and cleaning cleaned text changes nothing. `is_plain` asks the same of a file or folder name, without normalising it.
Declared by `interfaces/safe_text_interface.py::SafeTextInterface`.
"""

from __future__ import annotations

import unicodedata
from typing import Final

ELLIPSIS: Final = "..."
"""Three full stops rather than U+2026, which NFKC would turn into them: cleaning a cut text again
must not change it."""
MIN_LIMIT: Final = len(ELLIPSIS) + 1
RAW_FACTOR: Final = 4
"""At most `RAW_FACTOR * limit` characters of the raw text are read at all."""
MAX_MARKS: Final = 3
"""The most combining marks kept after one base character."""
INVISIBLE: Final = frozenset(
    {
        0x034F,  # combining grapheme joiner
        0x115F,  # Hangul choseong filler
        0x1160,  # Hangul jungseong filler (NFKC's form of U+3164 and U+FFA0)
        0x17B4,  # Khmer vowel inherent aq
        0x17B5,  # Khmer vowel inherent aa
        0x2800,  # Braille pattern blank
        0x3164,  # Hangul filler
        0xFFA0,  # halfwidth Hangul filler
        *range(0x180B, 0x1810),  # Mongolian free variation selectors
        *range(0xFE00, 0xFE10),  # variation selectors
        *range(0xE0100, 0xE01F0),  # variation selectors supplement
    }
)
"""Code points in an allowed category that render as nothing."""
_VISIBLE: Final = frozenset("LNPS")
_MARK: Final = "M"


class SafeText:
    """Declared by `interfaces/safe_text_interface.py::SafeTextInterface`."""

    def clean(self, text: str, limit: int) -> str:
        if limit < MIN_LIMIT:
            raise ValueError(f"a text limit must be at least {MIN_LIMIT}, not {limit}")
        raw_limit = limit * RAW_FACTOR
        kept = self._keep(unicodedata.normalize("NFKC", text[:raw_limit]))
        line = " ".join(unicodedata.normalize("NFKC", kept).split())
        if len(text) <= raw_limit and len(line) <= limit:
            return line
        return line[: limit - len(ELLIPSIS)].rstrip() + ELLIPSIS

    def is_plain(self, text: str) -> bool:
        return bool(text) and self._keep(text) == text and text.isprintable()

    @staticmethod
    def _keep(text: str) -> str:
        """`text` with whitespace as plain spaces and only allowlisted characters kept."""
        kept: list[str] = []
        marks: int | None = None  # marks since the last visible base; None: no base before
        for char in text:
            if char.isspace():
                kept.append(" ")
                marks = None
                continue
            if ord(char) in INVISIBLE:
                continue
            major = unicodedata.category(char)[0]
            if major in _VISIBLE:
                kept.append(char)
                marks = 0
            elif major == _MARK and marks is not None and marks < MAX_MARKS:
                kept.append(char)
                marks += 1
        return "".join(kept)
