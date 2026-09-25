# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every lane on this computer, found where the loops write them.

A lane is one run of a `*loop` runner. Each writes `<cwd>/<state_dir>/runs/<run id>/
events.jsonl` (the descriptors' run-events template), and this finds them the way the VS
Code extension's `LaneTracker` does: in each root, and in every directory directly inside
it. A lane's position is its file's size in bytes -- the offset a reader resumes after
(sub-doctrine 10.g) -- never a timestamp.

What it reports is what the files prove and nothing more (10.f): `finished` when the
runner's last snapshot says the run ended, `running` when the file changed within
`quiet_after` seconds, `quiet` when it has not; a lane whose file is older than
`recent_within` is not listed. The transcript itself -- turns, tools, tokens -- is the
live feed's to tail (`vibey serve`'s lane stream), not this list's.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

QUIET_AFTER: Final = 120.0
"""Seconds without an event after which a running lane reads as quiet."""

RECENT_WITHIN: Final = 24 * 60 * 60.0
"""A lane whose last event is older than this many seconds is not listed."""

ENDED: Final[dict[str, str]] = {
    "completed": "completed",
    "failed": "failed",
    "winding_down": "stopped",
}
"""A runner snapshot's status, read as how the lane ended."""


@dataclass(frozen=True, slots=True)
class LaneEngine:
    """An engine a lane may belong to, and the directory its runner writes under."""

    engine_id: str
    state_dir: str


class LaneScanner:
    """Lists the lanes under `roots`.

    Declared by `interfaces/lanes_interface.py::LaneScannerInterface`."""

    def __init__(
        self,
        *,
        engines: Sequence[LaneEngine],
        roots: Sequence[Path],
        now: Callable[[], float],
        quiet_after: float = QUIET_AFTER,
        recent_within: float = RECENT_WITHIN,
    ) -> None:
        self._engines = tuple(engines)
        self._roots = tuple(roots)
        self._now = now
        self._quiet_after = quiet_after
        self._recent_within = recent_within

    def lanes(self) -> list[dict[str, object]]:
        """Every recent lane, newest first."""
        now = self._now()
        found: dict[Path, dict[str, object]] = {}
        for events, engine, cwd, run_id in self._discover():
            if events in found:
                continue
            stat = events.stat()
            if now - stat.st_mtime > self._recent_within:
                continue
            outcome = self._outcome(events.parent)
            state = (
                "finished"
                if outcome is not None
                else "quiet"
                if now - stat.st_mtime > self._quiet_after
                else "running"
            )
            found[events] = {
                "id": run_id,
                "engine": engine.engine_id,
                "cwd": str(cwd),
                "events_path": str(events),
                "label": f"{cwd.name} · {engine.engine_id}",
                "state": state,
                "outcome": outcome,
                "offset": stat.st_size,
                "last_event_at": stat.st_mtime,
            }
        return sorted(found.values(), key=self._last_event, reverse=True)

    def _discover(self) -> list[tuple[Path, LaneEngine, Path, str]]:
        found: list[tuple[Path, LaneEngine, Path, str]] = []
        for root in self._roots:
            for cwd in (root, *self._children(root)):
                for engine in self._engines:
                    for run in self._children(cwd / engine.state_dir / "runs"):
                        events = run / "events.jsonl"
                        if events.is_file():
                            found.append((events, engine, cwd, run.name))
        return found

    @staticmethod
    def _last_event(lane: dict[str, object]) -> float:
        value = lane["last_event_at"]
        return value if isinstance(value, float) else 0.0

    @staticmethod
    def _children(directory: Path) -> list[Path]:
        try:
            return sorted(
                entry
                for entry in directory.iterdir()
                # A symlink is never walked: it could lead the scan out of its root.
                if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith(".")
            )
        except OSError:
            return []

    @staticmethod
    def _outcome(run: Path) -> str | None:
        try:
            snapshot = json.loads((run / "snapshots" / "latest.json").read_text())
        except (OSError, ValueError):
            return None
        status = snapshot.get("status") if isinstance(snapshot, dict) else None
        return ENDED.get(status) if isinstance(status, str) else None
