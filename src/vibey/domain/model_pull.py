# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ollama's pull stream, turned into lines a person can read in a terminal or a log.

`POST /api/pull` streams one JSON object per line: a `status`, and while a layer downloads,
its `digest`, `total` and `completed` byte counts. A pull of the sovereign model is thousands of
them. `PullProgress` says each new stage once, and a layer's download every `step_percent`
percent, so `vibey install --model` reads the same under `curl | sh` as in a terminal.

Pure: no I/O, no clock. Declared by `interfaces/model_pull_interface.py` (ADR-0016).
"""

from collections.abc import Mapping
from typing import Final

DEFAULT_STEP_PERCENT: Final = 10
_BYTES_PER_GB: Final = 1e9


class PullProgress:
    """Reports one pull. Keep one per pull: it remembers what it has already said."""

    def __init__(self, step_percent: int = DEFAULT_STEP_PERCENT) -> None:
        self._step = step_percent
        self._status = ""
        self._digest = ""
        self._reported = -1

    def line(self, event: Mapping[str, object]) -> str | None:
        """The line to print for `event`, or None when it adds nothing."""
        status = str(event.get("status", ""))
        total, completed = event.get("total"), event.get("completed")
        if isinstance(total, int) and total > 0 and isinstance(completed, int):
            return self._download(status, str(event.get("digest", status)), total, completed)
        if not status or status == self._status:
            return None
        self._status = status
        return status

    def _download(self, status: str, digest: str, total: int, completed: int) -> str | None:
        self._status = status
        if digest != self._digest:
            self._digest, self._reported = digest, -1
        percent = min(completed * 100 // total, 100)
        step = percent // self._step * self._step
        if step <= self._reported:
            return None
        self._reported = step
        return f"{status}: {percent}% of {total / _BYTES_PER_GB:.1f} GB"
