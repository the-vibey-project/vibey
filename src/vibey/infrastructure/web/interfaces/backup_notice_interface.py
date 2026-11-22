# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/backup_notice.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class BackupNoticeInterface(Protocol):
    """Says, once per process, that a query went to the Brave backup."""

    def announce(self, reason: str) -> str | None:
        """The sentence, when this call is the one that said it; else None."""
        ...
