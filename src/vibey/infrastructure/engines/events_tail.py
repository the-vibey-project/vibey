# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Follows an append-only events.jsonl by byte offset, so a half-written line is not lost.

Re-reading the whole file and counting lines read a line the engine was still writing,
failed to parse it once, and never came back to it. This reads only the bytes appended
since the last call and returns a line only once its newline has arrived.
"""

from pathlib import Path


class EventsTail:
    """Complete lines of a growing file, each returned exactly once."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._offset = 0
        self._pending = b""

    def read_new(self) -> list[str]:
        try:
            with self._path.open("rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except FileNotFoundError:
            return []
        self._offset += len(chunk)
        *complete, self._pending = (self._pending + chunk).split(b"\n")
        return [line.decode("utf-8", errors="replace") for line in complete]

    def flush(self) -> list[str]:
        remainder, self._pending = self._pending, b""
        return [remainder.decode("utf-8", errors="replace")] if remainder else []
