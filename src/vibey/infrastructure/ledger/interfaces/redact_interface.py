# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams implemented by the free-text credential redactor in `ledger/redact.py`."""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class TextRunIndexInterface(Protocol):
    """Where each maximal run of a character class ends, in one piece of text."""

    def end(self, char_class: str, index: int) -> int:
        """The first index at or after `index` whose character is not in `char_class` (a
        regex character-class body, such as `A-Za-z0-9`): `index` itself when that
        character is not in the class, or `index` is the end of the text."""
        ...


@runtime_checkable
class CredentialShapeInterface(Protocol):
    """One vendor's credential: a short prefix, then character-class runs."""

    def matches(self, text: str, runs: TextRunIndexInterface) -> Iterator[tuple[int, int]]:
        """Every `(start, stop)` match in `text`, one per start, including one that starts
        inside another; each costs one run lookup per segment, never a rescan."""
        ...


@runtime_checkable
class SecretTextRedactorInterface(Protocol):
    """Replaces every credential-shaped run in a piece of text with the redaction marker.

    Pure: no I/O. The result does not depend on the order the credential shapes are
    tried in, redacting it again changes nothing, and the cost is O(n log n) in the
    length of the text, never quadratic.
    """

    def redact(self, text: str) -> str:
        """The text with every credential-shaped run replaced by one marker."""
        ...

    def spans(self, text: str) -> list[tuple[int, int]]:
        """The sorted, non-overlapping `(start, stop)` runs `redact` replaces, one per marker."""
        ...
