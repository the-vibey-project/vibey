# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Append-only filesystem run storage."""

import json
from pathlib import Path
from typing import Any

from qwenloop.domain.model import FollowUp


class FileRunStore:
    def __init__(self, cwd: Path) -> None:
        self._root = cwd / ".qwenloop" / "runs"

    def _run_dir(self, run_id: str) -> Path:
        return self._root / run_id

    def create(self, run_id: str, metadata: dict[str, object]) -> Path:
        run_dir = self._run_dir(run_id)
        (run_dir / "snapshots").mkdir(parents=True, exist_ok=True)
        (run_dir / "control" / "inbox").mkdir(parents=True, exist_ok=True)
        (run_dir / "control" / "ack").mkdir(parents=True, exist_ok=True)
        meta = run_dir / "meta.json"
        if not meta.exists():
            meta.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (run_dir / "events.jsonl").touch(exist_ok=True)
        return run_dir

    def append_event(self, run_id: str, event: dict[str, object]) -> None:
        path = self._run_dir(run_id) / "events.jsonl"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")

    def write_snapshot(self, run_id: str, snapshot: dict[str, object]) -> None:
        target = self._run_dir(run_id) / "snapshots" / "latest.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(target)

    def read_control(self, run_id: str) -> list[dict[str, object]]:
        inbox = self._run_dir(run_id) / "control" / "inbox"
        if not inbox.exists():
            return []
        commands: list[dict[str, object]] = []
        for path in sorted(inbox.glob("*.json")):
            try:
                value: Any = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    commands.append(value)
            except (OSError, json.JSONDecodeError):
                continue
        return commands

    def take_prompts(self, run_id: str) -> list[FollowUp]:
        """Pending `prompt` controls, oldest first (their names begin with the time they were
        sent). Each is moved to `control/ack` as it is taken, so a follow-up reaches the model
        once, even if the process starts again. Anything else in the inbox is left alone."""
        control = self._run_dir(run_id) / "control"
        inbox = control / "inbox"
        if not inbox.exists():
            return []
        taken: list[FollowUp] = []
        for path in sorted(inbox.glob("*.json")):
            try:
                value: Any = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(value, dict) or value.get("type") != "prompt":
                continue
            text = value.get("text")
            if not isinstance(text, str):
                continue
            (control / "ack").mkdir(parents=True, exist_ok=True)
            path.replace(control / "ack" / path.name)
            taken.append(FollowUp(id=path.stem, text=text))
        return taken
