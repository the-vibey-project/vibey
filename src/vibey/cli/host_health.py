# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s host-health section: the newest weekly record, its age and the forecast.

Which record: `[host_health] record` in `./vibey.toml` when it is set; else the host's own
record (`~/.local/state/vibey/host-health/records.jsonl`, what the weekly unit appends to);
else, in a vibey checkout, the committed `docs/architecture/evidence/host-health.jsonl`.
`[host_health] max_age_days` (default 14) is how old the newest record may be, and
`[host_health] required = true` turns a missing or stale record from a WARN into a FAIL.
"""

import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from vibey.cli.interfaces.host_health_interface import HostHealthDoctorInterface
from vibey.domain.host_health import COMMITTED_RECORD, DEFAULT_LOCAL_RECORD, HostHealthReport
from vibey.domain.interfaces.host_health_interface import HostHealthReportInterface

DEFAULT_MAX_AGE_DAYS: Final = 14


class HostHealthDoctor(HostHealthDoctorInterface):
    """Reads `./vibey.toml` and the record, and hands both to the pure report."""

    def __init__(
        self,
        *,
        root: Path | None = None,
        home: Path | None = None,
        clock: Callable[[], datetime] | None = None,
        report: HostHealthReportInterface | None = None,
    ) -> None:
        self._root = root
        self._home = home
        self._clock = clock or (lambda: datetime.now(UTC))
        self._report = report or HostHealthReport()

    def _cwd(self) -> Path:
        return self._root if self._root is not None else Path.cwd()

    def _expand(self, text: str) -> Path:
        home = self._home if self._home is not None else Path.home()
        return home / text[1:].lstrip("/") if text.startswith("~") else Path(text)

    def _table(self) -> dict[str, Any]:
        path = self._cwd() / "vibey.toml"
        if not path.is_file():
            return {}
        table = tomllib.loads(path.read_text(encoding="utf-8")).get("host_health", {})
        return table if isinstance(table, dict) else {}

    def record_path(self) -> tuple[Path | None, str]:
        declared = self._table().get("record")
        if declared:
            path = self._expand(str(declared))
            return (path if path.is_absolute() else self._cwd() / path), "[host_health] record"
        local = self._expand(DEFAULT_LOCAL_RECORD)
        if local.is_file():
            return local, "the host's own record"
        committed = self._cwd() / COMMITTED_RECORD
        if committed.is_file():
            return committed, "the committed record"
        return None, f"neither {DEFAULT_LOCAL_RECORD} nor ./{COMMITTED_RECORD} exists"

    def doctor_lines(self) -> tuple[list[str], bool]:
        try:
            table = self._table()
            path, source = self.record_path()
        except (tomllib.TOMLDecodeError, OSError) as exc:
            return [f"FAIL {'host-health':<20} ./vibey.toml is unreadable: {exc}"], False
        text = ""
        if path is not None:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                source = f"{path} is unreadable: {exc}"
        summary = self._report.newest(text)
        where = str(path) if path is not None and summary is not None else source
        return self._report.doctor_lines(
            summary,
            source=where,
            now=self._clock(),
            max_age_days=int(table.get("max_age_days", DEFAULT_MAX_AGE_DAYS)),
            required=bool(table.get("required", False)),
        )


HOST_HEALTH: Final[HostHealthDoctorInterface] = HostHealthDoctor()
"""What `vibey doctor` runs. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
