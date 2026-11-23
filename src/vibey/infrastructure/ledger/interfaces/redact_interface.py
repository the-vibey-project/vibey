# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams implemented by the free-text credential redactor in `ledger/redact.py`."""

import re
from collections.abc import Callable, Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class RunCursorInterface(Protocol):
    """Where a run of one character class ends, for lookups that never move backwards."""

    @property
    def scanned(self) -> int:
        """How many characters of the text this cursor has examined so far."""
        ...

    def end(self, index: int) -> int:
        """The first index at or after `index` whose character is not in the class: `index`
        itself when that character is not in it, or `index` is the end of the text."""
        ...


RunCursorFactory = Callable[[str, re.Pattern[str]], RunCursorInterface]
"""Makes a cursor over a text for one run pattern (a compiled `[class]*`)."""


@runtime_checkable
class CredentialShapeInterface(Protocol):
    """One vendor's credential: a short prefix, then character-class runs."""

    @property
    def prefix(self) -> str:
        """The regex every match starts with; it matches a bounded amount of text."""
        ...

    def matches(self, text: str, cursor_factory: RunCursorFactory) -> Iterator[tuple[int, int]]:
        """Every `(start, stop)` match in `text` in start order, one per start, including one
        that starts inside another; each costs one cursor lookup per segment."""
        ...


@runtime_checkable
class SecretTextRedactorInterface(Protocol):
    """Replaces every credential-shaped run in a piece of text with the redaction marker.

    Pure: no I/O. The result does not depend on the order the credential shapes are
    tried in, redacting it again changes nothing, and time and memory are linear in the
    length of the text.
    """

    def redact(self, text: str) -> str:
        """The text with every credential-shaped run replaced by one marker."""
        ...

    def spans(self, text: str) -> list[tuple[int, int]]:
        """The sorted, non-overlapping `(start, stop)` runs `redact` replaces, one per marker."""
        ...
