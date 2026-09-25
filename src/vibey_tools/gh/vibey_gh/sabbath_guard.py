# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Sabbath as this host keeps it: the window built for this machine, the lanes that
rest in it, and what re-arms when it ends (sub-doctrine 8.i; vibey ADR-0072).

`vibey_gh.sabbath` is the pure computation; this is where it meets the machine -- the
host's zone, its location (`vibey_gh.sabbath_location`), the clock -- and where the
heartbeat's rest and resume are decided:

- **During the window** the heartbeat keeps beating but publishes nothing: it records
  "resting until <sundown Saturday>" so a liveness check reads rest, not death (10.f).
- **At the first beat after it**, the heartbeat re-arms: it re-fires the held merge train
  and promotion (`[sabbath] resume_dispatch`) and runs every lane registered as paused.
  Each lane's file is removed only after its resume command succeeds, so a beat that dies
  mid-resume re-runs it on the next beat (idempotent under replay).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from vibey_gh.config import GhConfig, SabbathConfig
from vibey_gh.interfaces.sabbath_guard_interface import (
    SabbathGuardInterface,
    SabbathLanesInterface,
)
from vibey_gh.interfaces.sabbath_location_interface import (
    LocationSourceInterface,
    ResolvedLocationInterface,
)
from vibey_gh.interfaces.sabbath_window_interface import RestWindowInterface
from vibey_gh.sabbath import SabbathWindow
from vibey_gh.sabbath_location import (
    LocationResolver,
    OsLocationService,
    OverrideLocation,
    ZoneTabLocation,
    host_zone,
)

__all__ = ["SabbathGuard", "SabbathLanes"]

Runner = Callable[[Sequence[str], str | None], tuple[int, str]]
_LANE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _run(argv: Sequence[str], cwd: str | None) -> tuple[int, str]:
    try:
        done = subprocess.run(
            list(argv), cwd=cwd, capture_output=True, text=True, timeout=600, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return done.returncode, (done.stdout + done.stderr).strip()


def _clock_time(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


class SabbathGuard(SabbathGuardInterface):
    """The window for this host, and the one question every writer asks of it."""

    def __init__(
        self,
        config: SabbathConfig,
        *,
        home: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        environ: Mapping[str, str] | None = None,
        platform: str = sys.platform,
        os_service: LocationSourceInterface | None = None,
        zone_tables: Sequence[Path] | None = None,
    ) -> None:
        self._config = config
        self._home = home
        self._clock = clock
        self._environ = os.environ if environ is None else environ
        self._platform = platform
        self._os_service = os_service
        self._zone_tables = zone_tables
        self._location: ResolvedLocationInterface | None = None
        self._window: SabbathWindow | None = None

    def _expand(self, declared: str) -> Path:
        return Path(
            declared.replace("~", str(self._home), 1) if declared.startswith("~") else declared
        )

    def zone_name(self) -> str:
        return self._config.timezone or host_zone(self._environ)

    def _override(self) -> OverrideLocation:
        lat_env = self._environ.get("VIBEY_SABBATH_LATITUDE", "")
        lon_env = self._environ.get("VIBEY_SABBATH_LONGITUDE", "")
        if lat_env and lon_env:
            return OverrideLocation(float(lat_env), float(lon_env))
        path = self._expand(self._config.local_config)
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return OverrideLocation(None, None)
        section = data.get("sabbath", data)
        lat, lon = section.get("latitude"), section.get("longitude")
        if lat is None or lon is None:
            return OverrideLocation(None, None)
        return OverrideLocation(float(lat), float(lon))

    def location(self) -> ResolvedLocationInterface | None:
        """Where this host stands, from the first source that answers (see the module)."""
        if self._location is None:
            sources: list[LocationSourceInterface] = [self._override()]
            if self._config.location_service:
                sources.append(
                    self._os_service
                    if self._os_service is not None
                    else OsLocationService(platform=self._platform)
                )
            tables = self._zone_tables
            sources.append(
                ZoneTabLocation(self.zone_name())
                if tables is None
                else ZoneTabLocation(self.zone_name(), tables)
            )
            cache = self._expand(self._config.lanes_dir).parent / "sabbath-location.json"
            resolver = LocationResolver(
                sources,
                zone=self.zone_name(),
                clock=lambda: self._clock().timestamp(),
                cache=cache,
            )
            self._location = resolver.resolve()
        return self._location

    def window(self) -> SabbathWindow:
        if self._window is None:
            name = self.zone_name()
            try:
                zone = ZoneInfo(name) if name else None
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError(
                    f"sabbath.timezone {name!r} is not a zone this machine knows"
                ) from exc
            where = self.location()
            margin = self._config.offset_minutes
            if where is None or where.coarse:
                margin += self._config.coarse_margin_minutes
            self._window = SabbathWindow(
                latitude=None if where is None else where.latitude,
                longitude=None if where is None else where.longitude,
                zone=zone,
                margin=timedelta(minutes=margin),
                fallback_opens=_clock_time(self._config.fallback_opens),
                fallback_closes=_clock_time(self._config.fallback_closes),
                enabled=self._config.enabled,
                location="unresolved" if where is None else where.describe(),
            )
        return self._window

    def hold(self, at: datetime | None = None) -> RestWindowInterface | None:
        """The window holding `at` (the clock when omitted), or None to proceed."""
        return self.window().hold(self._clock() if at is None else at)

    def describe(self) -> list[str]:
        """What `vibey-gh sabbath status` and a doctor print."""
        window = self.window()
        where = self.location()
        now = self._clock()
        lines = [
            f"sabbath: {'enabled' if window.enabled else 'DISABLED by [sabbath] enabled = false'}",
            f"zone: {self.zone_name() or 'unresolved (local mean solar time)'}",
            f"location: {'unresolved -- declared fallback times apply' if where is None else where.describe()}",
        ]
        held = window.hold(now)
        if held is not None:
            lines.append(f"resting now: until {held.resumes.isoformat()} ({held.basis})")
        else:
            lines.append(f"next rest ends: {window.next_resume(now).isoformat()}")
        return lines


class SabbathLanes(SabbathLanesInterface):
    """Lanes paused for the Sabbath, each with the command that resumes it."""

    def __init__(self, directory: Path, *, run: Runner = _run) -> None:
        self._dir = directory
        self._run = run

    def register(self, name: str, command: Sequence[str], cwd: str | None = None) -> Path:
        if _LANE_NAME.fullmatch(name) is None:
            raise ValueError(f"lane name {name!r} must be letters, digits, '.', '_' or '-'")
        if not command:
            raise ValueError("a paused lane needs the command that resumes it")
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{name}.json"
        body = {"name": name, "command": list(command), "cwd": cwd}
        partial = path.with_name(f".{path.name}.partial")
        partial.write_text(json.dumps(body) + "\n", encoding="utf-8")
        os.replace(partial, path)
        return path

    def pending(self) -> list[tuple[str, list[str], str | None]]:
        if not self._dir.is_dir():
            return []
        found = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
                found.append(
                    (str(body["name"]), [str(a) for a in body["command"]], body.get("cwd"))
                )
            except (OSError, ValueError, KeyError, TypeError):
                found.append((path.stem, [], None))
        return found

    def resume(self) -> list[str]:
        """Run every paused lane's resume command; forget a lane only once it succeeded."""
        lines = []
        for name, command, cwd in self.pending():
            if not command:
                lines.append(f"lane {name}: unreadable registration, left in place")
                continue
            code, out = self._run(command, cwd)
            if code == 0:
                (self._dir / f"{name}.json").unlink(missing_ok=True)
                lines.append(f"lane {name}: resumed")
            else:
                tail = out.splitlines()[-1] if out else ""
                lines.append(f"lane {name}: resume exited {code}, kept for the next beat: {tail}")
        return lines


def resume_dispatch(cfg: GhConfig, *, cwd: str | None, run: Runner = _run) -> list[str]:
    """Re-fire the merge train and the promotion the window held. A module function because
    it is one `gh` call per workflow and holds no state of its own."""
    lines = []
    for workflow in (cfg.workflow_names.merge_train, cfg.workflow_names.promote):
        code, out = run(("gh", "workflow", "run", workflow), cwd)
        verdict = (
            "dispatched"
            if code == 0
            else f"not dispatched ({out.splitlines()[-1] if out else code})"
        )
        lines.append(f"{workflow}: {verdict}")
    return lines
