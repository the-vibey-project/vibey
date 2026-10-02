# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey doctor` says about the machine's health (scripts/host_health.py).

The weekly host-health run appends one JSON line per week, each carrying the forecast as of
that run. This reads the newest line and turns it into the doctor's lines: how old it is,
what was measured and skipped, when the machine is predicted to need replacing and which
driver binds, and any hypothesis the record offers -- printed as a note, never a finding. A record that is missing or older than the declared age is said out
loud (a WARN, or a FAIL with `[host_health] required = true`), never passed over (12.e).
Pure: the caller reads the file and passes the time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from vibey.domain.interfaces.host_health_interface import HostHealthReportInterface

SCHEMA: Final = "vibey-host-health/1"
DEFAULT_LOCAL_RECORD: Final = "~/.local/state/vibey/host-health/records.jsonl"
"""The host's own record, as `[host_health] local_record` in scripts/host_health.toml
declares it; tests/scripts/test_host_health.py fails if the two disagree."""
COMMITTED_RECORD: Final = "docs/architecture/evidence/host-health.jsonl"
INSTALL_HINT: Final = (
    "`uv run --no-project --python 3.12 python scripts/host_health.py install` renders the"
    " weekly unit"
)
ATTENTION: Final = ("exceeded", "unconfirmed")


@dataclass(frozen=True)
class HostHealthSummary:
    """The newest record, reduced to what the doctor prints."""

    measured_at: datetime
    host: str
    counts: dict[str, int]
    binding: str | None
    replace_by: str | None
    earliest: str | None
    latest: str | None
    warning: bool
    drivers: tuple[dict[str, Any], ...]
    hypotheses: tuple[str, ...] = ()


class HostHealthReport(HostHealthReportInterface):
    """Declared by `interfaces/host_health_interface.py`."""

    def newest(self, text: str) -> HostHealthSummary | None:
        found: HostHealthSummary | None = None
        for line in text.splitlines():
            summary = self._parse(line)
            if summary is not None and (found is None or summary.measured_at >= found.measured_at):
                found = summary
        return found

    @staticmethod
    def _parse(line: str) -> HostHealthSummary | None:
        try:
            raw = json.loads(line)
        except ValueError:
            return None
        if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
            return None
        try:
            measured = datetime.fromisoformat(str(raw["measured_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            return None
        counts: dict[str, int] = {}
        for figure in raw.get("figures", []):
            status = str(figure.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
        host = raw.get("host", {})
        name = " · ".join(
            str(host[key]) for key in ("model", "chip", "os") if host.get(key)
        ) or str(host.get("fingerprint", "unknown host"))
        forecast = raw.get("forecast", {})
        return HostHealthSummary(
            measured_at=measured.astimezone(UTC),
            host=name,
            counts=counts,
            binding=forecast.get("binding"),
            replace_by=forecast.get("replace_by"),
            earliest=forecast.get("earliest"),
            latest=forecast.get("latest"),
            warning=bool(forecast.get("warning", False)),
            drivers=tuple(d for d in forecast.get("drivers", []) if isinstance(d, dict)),
            hypotheses=tuple(str(h) for h in forecast.get("hypotheses", [])),
        )

    def doctor_lines(
        self,
        summary: HostHealthSummary | None,
        *,
        source: str,
        now: datetime,
        max_age_days: int,
        required: bool,
    ) -> tuple[list[str], bool]:
        mark = "FAIL" if required else "WARN"
        if summary is None:
            return (
                [f"{mark} {'host-health':<20} no host-health record at {source} -- {INSTALL_HINT}"],
                not required,
            )
        age = (now - summary.measured_at).total_seconds() / 86400
        counts = ", ".join(f"{n} {s}" for s, n in sorted(summary.counts.items()))
        fresh = age <= max_age_days
        state = "PASS" if fresh else mark
        lines = [
            f"{state} {'host-health':<20} newest record {summary.measured_at.date().isoformat()}"
            f" ({age:.1f} days old) on {summary.host}: {counts} ({source})"
        ]
        if not fresh:
            lines[0] += f" -- older than {max_age_days} days: is the weekly unit loaded?"
        lines.append(self._forecast_line(summary))
        for driver in summary.drivers:
            if driver.get("state") in ATTENTION:
                detail = driver.get("reason") or (
                    f"{driver.get('value')} against {driver.get('threshold')}"
                )
                lines.append(
                    f"WARN {'host-health-driver':<20} {driver.get('label')}: {driver.get('state')}"
                    f" ({detail})"
                )
        # Offered by the record as hypotheses, never as findings: printed as notes, and they
        # never change the verdict.
        lines.extend(f"NOTE {'host-health-hypothesis':<20} {text}" for text in summary.hypotheses)
        return lines, fresh or not required

    @staticmethod
    def _forecast_line(summary: HostHealthSummary) -> str:
        if summary.binding is None:
            waiting = sum(1 for d in summary.drivers if d.get("state") == "insufficient-history")
            return (
                f"PASS {'host-health-forecast':<20} no driver projects a replacement date yet"
                f" ({waiting} trend driver(s) still gathering weekly history)"
            )
        label = next(
            (str(d.get("label")) for d in summary.drivers if d.get("id") == summary.binding),
            summary.binding,
        )
        mark = "WARN" if summary.warning else "PASS"
        return (
            f"{mark} {'host-health-forecast':<20} replace by {summary.replace_by}"
            f" ({summary.earliest} to {summary.latest or 'not bounded'}), bound by {label}"
        )
