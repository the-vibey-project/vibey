# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s host-health section: which record it reads, and what it does when it
cannot read one."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibey.cli.host_health import HostHealthDoctor
from vibey.domain.host_health import COMMITTED_RECORD, DEFAULT_LOCAL_RECORD, SCHEMA

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def record(measured_at: str = "2026-10-05T06:41:00.000Z") -> str:
    return json.dumps(
        {
            "schema": SCHEMA,
            "measured_at": measured_at,
            "host": {"fingerprint": "sha256:abc", "model": "Mac17,2"},
            "figures": [{"id": "a", "status": "measured"}],
            "forecast": {"binding": None, "drivers": []},
        }
    )


def doctor(root: Path, home: Path) -> HostHealthDoctor:
    return HostHealthDoctor(root=root, home=home, clock=lambda: NOW)


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    root, home = tmp_path / "checkout", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    return root, home


def test_nothing_anywhere_is_a_warning_naming_where_it_looked(dirs: tuple[Path, Path]) -> None:
    lines, ok = doctor(*dirs).doctor_lines()
    assert ok
    assert lines[0].startswith("WARN host-health")
    assert DEFAULT_LOCAL_RECORD in lines[0] and COMMITTED_RECORD in lines[0]


def test_the_hosts_own_record_wins_over_the_committed_one(dirs: tuple[Path, Path]) -> None:
    root, home = dirs
    local = home / DEFAULT_LOCAL_RECORD[2:]
    local.parent.mkdir(parents=True)
    local.write_text(record("2026-10-05T06:41:00.000Z") + "\n", encoding="utf-8")
    committed = root / COMMITTED_RECORD
    committed.parent.mkdir(parents=True)
    committed.write_text(record("2026-09-01T06:41:00.000Z") + "\n", encoding="utf-8")
    probe = doctor(root, home)
    assert probe.record_path() == (local, "the host's own record")
    lines, ok = probe.doctor_lines()
    assert ok and lines[0].startswith("PASS host-health") and str(local) in lines[0]
    local.unlink()
    assert probe.record_path() == (committed, "the committed record")


def test_vibey_toml_declares_the_record_its_age_and_whether_it_is_required(
    dirs: tuple[Path, Path],
) -> None:
    root, home = dirs
    (root / "vibey.toml").write_text(
        '[host_health]\nrecord = "health.jsonl"\nmax_age_days = 1\nrequired = true\n',
        encoding="utf-8",
    )
    (root / "health.jsonl").write_text(record() + "\n", encoding="utf-8")
    probe = doctor(root, home)
    assert probe.record_path() == (root / "health.jsonl", "[host_health] record")
    lines, ok = probe.doctor_lines()
    assert not ok and lines[0].startswith("FAIL host-health") and "older than 1 days" in lines[0]
    (root / "vibey.toml").write_text('[host_health]\nrecord = "~/h.jsonl"\n', encoding="utf-8")
    assert probe.record_path() == (home / "h.jsonl", "[host_health] record")


def test_a_table_that_is_not_a_table_is_ignored(dirs: tuple[Path, Path]) -> None:
    root, home = dirs
    (root / "vibey.toml").write_text('host_health = "nope"\n', encoding="utf-8")
    lines, ok = doctor(root, home).doctor_lines()
    assert ok and lines[0].startswith("WARN host-health")


def test_an_unreadable_vibey_toml_fails_out_loud(dirs: tuple[Path, Path]) -> None:
    root, home = dirs
    (root / "vibey.toml").write_text("[host_health\n", encoding="utf-8")
    lines, ok = doctor(root, home).doctor_lines()
    assert not ok and lines[0].startswith("FAIL host-health") and "unreadable" in lines[0]


def test_an_unreadable_record_says_so(dirs: tuple[Path, Path]) -> None:
    root, home = dirs
    (root / "vibey.toml").write_text('[host_health]\nrecord = "dir"\n', encoding="utf-8")
    (root / "dir").mkdir()
    lines, ok = doctor(root, home).doctor_lines()
    assert ok and "is unreadable" in lines[0]


def test_the_defaults_read_the_real_clock_and_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    probe = HostHealthDoctor()
    assert probe.record_path()[0] is None
    lines, ok = probe.doctor_lines()
    assert ok and lines[0].startswith("WARN host-health")
