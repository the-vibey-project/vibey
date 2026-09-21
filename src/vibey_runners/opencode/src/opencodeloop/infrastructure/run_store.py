# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Append-only filesystem state for the generic Vibey loop adapter."""

import json
from datetime import UTC, datetime
from pathlib import Path

from opencodeloop.domain.model import DONE_MARKER, RunResult

SCHEMA_VERSION = 1


class FileRunStore:
    """Write the stable `events.jsonl`, `meta.json`, and snapshot contract."""

    def begin(self, run_dir: Path, run_id: str, cwd: Path, session_id: str | None) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "snapshots").mkdir(exist_ok=True)
        (run_dir / "inbox").mkdir(exist_ok=True)
        self._write_json(
            run_dir / "meta.json",
            {
                "run_id": run_id,
                "schema_version": SCHEMA_VERSION,
                "cwd": str(cwd),
                "session_id": session_id,
                "status": "active",
                "updated_at": self._now(),
            },
        )

    def append_event(self, run_dir: Path, event: dict[str, object]) -> None:
        record = {"timestamp": self._now(), **event}
        with (run_dir / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    def finish(self, run_dir: Path, result: RunResult) -> None:
        status = result.status.value
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "returncode": result.returncode,
            "session_id": result.session_id,
            "detail": result.detail,
            "done_marker": DONE_MARKER if result.succeeded else None,
            "updated_at": self._now(),
        }
        self._write_json(run_dir / "meta.json", metadata, merge=True)
        self._write_json(run_dir / "snapshots" / "latest.json", metadata)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _write_json(path: Path, value: dict[str, object], merge: bool = False) -> None:
        if merge and path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous.update(value)
            value = previous
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
