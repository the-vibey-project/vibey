# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The host's Sabbath gate, read from a LOCAL vibey.toml (8.i; ADR-0070). The coordinates
below are the labelled EXAMPLE fixture (Greenville, SC), never a default."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibey.infrastructure.interfaces.sabbath_interface import HostSabbathGateInterface
from vibey.infrastructure.sabbath import HostSabbathGate

EXAMPLE = 'latitude = 34.97\nlongitude = -82.44\ntimezone = "America/New_York"\n'


def _toml(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "vibey.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_a_local_sabbath_table_places_the_host_and_holds_friday_night(tmp_path: Path) -> None:
    friday_night = datetime(2026, 9, 26, 1, 0, tzinfo=UTC)
    gate = HostSabbathGate.from_table(
        {
            "latitude": 34.97,
            "longitude": -82.44,
            "timezone": "America/New_York",
            "lanes_dir": str(tmp_path / "lanes"),
        },
        home=tmp_path,
        environ={},
        clock=lambda: friday_night,
    )
    gate_seam: HostSabbathGateInterface = gate
    held = gate_seam.hold()
    assert held is not None and "configured override" in held.basis
    assert gate.location_resolved()
    assert any(line.startswith("resting now") for line in gate.describe())


def test_from_toml_reads_the_table_and_keeps_the_defaults_without_one(tmp_path: Path) -> None:
    path = _toml(tmp_path, f"[sabbath]\n{EXAMPLE}")
    assert HostSabbathGate.from_toml(path, home=tmp_path, environ={}).location_resolved()
    missing = HostSabbathGate.from_toml(tmp_path / "absent.toml", home=tmp_path, environ={})
    assert isinstance(missing, HostSabbathGate)


def test_a_bad_table_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'lattitude'"):
        HostSabbathGate.from_table({"lattitude": 1.0}, home=tmp_path)
    with pytest.raises(ValueError, match="must be a table"):
        HostSabbathGate.from_toml(_toml(tmp_path, 'sabbath = "on"\n'), home=tmp_path)
