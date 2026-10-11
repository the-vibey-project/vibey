# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for telling the wire log that an engine session has started."""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class SessionLogInterface(Protocol):
    """Notes, in the wire log, where an engine session writes what it does."""

    def started(
        self, *, engine: str, run_id: str, events_path: Path, work_item: str | None
    ) -> None:
        """One record per session; nothing at all when the wire log is not on."""
        ...
