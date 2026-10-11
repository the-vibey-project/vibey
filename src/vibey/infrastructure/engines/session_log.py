# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tells the wire log that an engine session started, so `vibey llm tail` can follow it.

The wire log (`wire_log.py`) holds what vibey's own sovereign client says to the model:
DESIGN and DECOMPOSE. A BUILD or REVIEW session is a separate process, the engine's runner,
and it writes its own events (each tool call, the streamed answer, the turn timings) to
`<worktree>/<state_dir>/runs/<run_id>/events.jsonl`. Nothing connected the two, so the tail
went quiet exactly when the long work began.

One `session` record per run closes that: it names the run's event file, and the tail
follows whichever session is newest, switching by itself when a new one starts. It carries
paths and ids only, nothing a redactor would need to touch, and does nothing unless the wire
log is on (`-vvv`, or `VIBEY_LLM_WIRE_LOG`).
"""

import json
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV, WIRE_LOG_VERSION


class SessionLog:
    """Declared by `interfaces/session_log_interface.py`. Diagnostics never fail the work: the
    first write error is said once on stderr and the log goes quiet."""

    def __init__(
        self,
        path: Path | None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._path = path
        self._clock = clock
        self._failed = False

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "SessionLog":
        """On when `VIBEY_LLM_WIRE_LOG` names a file, as the wire log itself is."""
        declared = (environ.get(WIRE_LOG_ENV) or "").strip()
        return cls(Path(declared).expanduser() if declared else None)

    def started(
        self, *, engine: str, run_id: str, events_path: Path, work_item: str | None
    ) -> None:
        if self._path is None or self._failed:
            return
        record: dict[str, Any] = {
            "v": WIRE_LOG_VERSION,
            "ts": self._clock().isoformat(),
            "kind": "session",
            "engine": engine,
            "run_id": run_id,
            "events_path": str(events_path),
            "work_item": work_item,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            self._failed = True
            sys.stderr.write(f"vibey: the LLM wire log {self._path} cannot be written ({exc})\n")
