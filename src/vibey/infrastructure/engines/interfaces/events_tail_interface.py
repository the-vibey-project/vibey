# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for following an append-only events.jsonl without losing a line."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventsTailInterface(Protocol):
    """Yields each complete line of a growing file exactly once."""

    def read_new(self) -> list[str]:
        """Complete lines written since the last call, without their newline.

        A final line that has no newline yet is held back until it is finished.
        """
        ...

    def flush(self) -> list[str]:
        """The held-back unterminated line, if any, returned once and cleared."""
        ...
