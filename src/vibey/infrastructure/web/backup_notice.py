# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sentence vibey says when a query leaves the local SearXNG for Brave: once per process.

A query that goes to Brave leaves the machine, so it is never silent. The first time in a
process (one `vibey search` run is one process; a worker is one for its life) the backup
answers, standard error gets one line:

    local SearXNG unavailable (<reason>); this query went to Brave Search

and every later Brave answer carries only its marker (`backend: brave`) in the structured
result. The line says "this query", never the query (queries can be private), and the reason is
vibey's own short text, cleaned to one line, never a URL.

Declared by `interfaces/backup_notice_interface.py` (ADR-0016).
"""

from __future__ import annotations

import sys
import threading
import unicodedata
from collections.abc import Callable
from typing import Final

REASON_CHARS: Final = 160


class BackupNotice:
    """Declared by `interfaces/backup_notice_interface.py::BackupNoticeInterface`."""

    def __init__(self, *, write: Callable[[str], None] | None = None) -> None:
        self._write = write if write is not None else self._stderr
        self._said = False
        self._lock = threading.Lock()

    def announce(self, reason: str) -> str | None:
        """Say the notice if it has not been said in this process; the sentence when this call
        said it, else None."""
        with self._lock:
            if self._said:
                return None
            self._said = True
        text = (
            f"local SearXNG unavailable ({self._cleaned(reason)}); this query went to Brave Search"
        )
        self._write(text)
        return text

    @staticmethod
    def _cleaned(reason: str) -> str:
        first = reason.strip().splitlines()[0] if reason.strip() else "unknown"
        first = "".join(" " if unicodedata.category(c)[0] in "CZ" else c for c in first)
        return first if len(first) <= REASON_CHARS else f"{first[: REASON_CHARS - 3]}..."

    @staticmethod
    def _stderr(text: str) -> None:
        print(text, file=sys.stderr)


PROCESS_BACKUP_NOTICE: Final = BackupNotice()
"""The notice every search in this process shares, so it is said once per process."""
