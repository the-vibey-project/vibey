# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over plugin text bound for a model context or a terminal (SP-LOOPS Task 6)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SafeTextInterface(Protocol):
    def clean(self, text: str, limit: int) -> str:
        """`text`, NFKC-normalised, as one line of allowlisted visible characters (letters,
        numbers, punctuation, symbols, plain spaces, and at most a few combining marks after a
        visible base), whitespace runs collapsed, at most `limit` characters; a cut text ends in
        an ellipsis. Idempotent. Raises `ValueError` for a `limit` too small for the ellipsis."""
        ...

    def is_plain(self, text: str) -> bool:
        """Whether a file or folder name is safe to show as it is: non-empty, and every
        character one `clean` would keep unchanged (plain spaces only, no normalising)."""
        ...
