# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s host-health report: the newest record, its age, and the forecast."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from vibey.domain.host_health import SCHEMA, HostHealthReport
from vibey.domain.interfaces.host_health_interface import HostHealthReportInterface

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def line(measured_at: str = "2026-10-05T06:41:00.000Z", **forecast: Any) -> str:
    return json.dumps(
        {
            "schema": SCHEMA,
            "run_id": f"sha256:abc@{measured_at}",
            "measured_at": measured_at,
            "host": {"fingerprint": "sha256:abc", "model": "Mac17,2", "chip": "Apple M5"},
            "figures": [
                {"id": "a", "status": "measured"},
                {"id": "b", "status": "measured"},
                {"id": "c", "status": "skipped"},
            ],
            "forecast": forecast,
        }
    )


def test_it_implements_its_interface() -> None:
    assert isinstance(HostHealthReport(), HostHealthReportInterface)


def test_newest_takes_the_latest_well_formed_line_and_skips_the_rest() -> None:
    text = "\n".join(
        [
            "not json",
            json.dumps([1, 2]),
            json.dumps({"schema": "other/1"}),
            json.dumps({"schema": SCHEMA}),
            json.dumps({"schema": SCHEMA, "measured_at": "yesterday"}),
            line("2026-10-05T06:41:00.000Z"),
            line("2026-09-28T06:41:00.000Z"),
        ]
    )
    summary = HostHealthReport().newest(text)
    assert summary is not None
    assert summary.measured_at == datetime(2026, 10, 5, 6, 41, tzinfo=UTC)
    assert summary.counts == {"measured": 2, "skipped": 1}
    assert summary.host == "Mac17,2 · Apple M5"
    assert HostHealthReport().newest("") is None


def test_a_host_with_no_description_is_named_by_its_fingerprint() -> None:
    raw = json.loads(line())
    raw["host"] = {"fingerprint": "sha256:abc"}
    summary = HostHealthReport().newest(json.dumps(raw))
    assert summary is not None and summary.host == "sha256:abc"


def test_a_missing_record_warns_or_fails_when_required() -> None:
    report = HostHealthReport()
    lines, ok = report.doctor_lines(
        None, source="nowhere", now=NOW, max_age_days=14, required=False
    )
    assert ok and lines[0].startswith("WARN host-health") and "install" in lines[0]
    lines, ok = report.doctor_lines(None, source="nowhere", now=NOW, max_age_days=14, required=True)
    assert not ok and lines[0].startswith("FAIL host-health")


def test_a_fresh_record_passes_and_says_no_date_is_projected_yet() -> None:
    drivers = [
        {"id": "battery", "label": "Battery", "state": "insufficient-history"},
        {"id": "swap", "label": "Swap", "state": "unconfirmed", "reason": "1 of 3"},
        {"id": "ram", "label": "Memory", "state": "exceeded", "value": 16, "threshold": 24},
        "not a driver",
    ]
    report = HostHealthReport()
    summary = report.newest(line(binding=None, drivers=drivers))
    lines, ok = report.doctor_lines(summary, source="rec", now=NOW, max_age_days=14, required=True)
    assert ok
    assert lines[0].startswith("PASS host-health") and "3.2 days old" in lines[0]
    assert "no driver projects a replacement date yet (1 trend driver(s)" in lines[1]
    assert "WARN host-health-driver   Swap: unconfirmed (1 of 3)" in lines
    assert "WARN host-health-driver   Memory: exceeded (16 against 24)" in lines


def test_a_stale_record_and_a_near_replacement_are_both_said_out_loud() -> None:
    drivers = [{"id": "throughput", "label": "Generation rate", "state": "projected"}]
    report = HostHealthReport()
    summary = report.newest(
        line(
            "2026-09-01T06:41:00.000Z",
            binding="throughput",
            replace_by="2027-01-01",
            earliest="2026-12-01",
            latest=None,
            warning=True,
            drivers=drivers,
        )
    )
    lines, ok = report.doctor_lines(summary, source="rec", now=NOW, max_age_days=14, required=False)
    assert ok
    assert lines[0].startswith("WARN host-health") and "is the weekly unit loaded?" in lines[0]
    assert lines[1] == (
        "WARN host-health-forecast replace by 2027-01-01 (2026-12-01 to not bounded),"
        " bound by Generation rate"
    )
    lines, ok = report.doctor_lines(summary, source="rec", now=NOW, max_age_days=14, required=True)
    assert not ok and lines[0].startswith("FAIL host-health")


def test_a_binding_driver_missing_from_the_list_is_named_by_its_id() -> None:
    report = HostHealthReport()
    summary = report.newest(
        line(
            binding="os_support",
            replace_by="2029-05-01",
            earliest="2029-05-01",
            latest="2029-05-01",
            warning=False,
            drivers=[],
        )
    )
    lines, _ = report.doctor_lines(summary, source="rec", now=NOW, max_age_days=14, required=False)
    assert lines[1] == (
        "PASS host-health-forecast replace by 2029-05-01 (2029-05-01 to 2029-05-01),"
        " bound by os_support"
    )
