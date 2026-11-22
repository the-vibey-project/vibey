# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam implemented by the free-text credential redactor in `ledger/redact.py`."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretTextRedactorInterface(Protocol):
    """Replaces every credential-shaped run in a piece of text with the redaction marker.

    Pure: no I/O. The result does not depend on the order the credential shapes are
    tried in, and redacting it again changes nothing.
    """

    def redact(self, text: str) -> str:
        """The text with every credential-shaped run replaced by one marker."""
        ...

    def spans(self, text: str) -> list[tuple[int, int]]:
        """The sorted, non-overlapping `(start, stop)` runs `redact` replaces, one per marker."""
        ...
