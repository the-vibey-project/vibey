# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[autonomy]`: the operator's standing grant is a section vibey-gh reads and validates,
and `doctor` judges `[autonomy]` and `[estimate.forecast]` as the loader does."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from vibey_gh import doctor
from vibey_gh.config import AutonomyConfig, load_config

GRANT = """
[autonomy]
standing_grant = true
operator_role = "pushes things along"
scope = ["build, test, open pull requests"]
never = ["--admin", "approving its own pull request"]
"""


def _write(root: Path, text: str) -> Path:
    (root / ".vibey-gh.toml").write_text(text, encoding="utf-8")
    return root


def _messages(root: Path) -> list[str]:
    return [dataclasses.astuple(f)[1] for f in doctor._check_unknown_keys(root)]


def test_no_table_means_no_grant(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, ""))
    assert cfg.autonomy == AutonomyConfig()
    assert cfg.autonomy.standing_grant is False


def test_the_grant_is_read_as_declared(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, GRANT))
    assert cfg.autonomy.standing_grant is True
    assert cfg.autonomy.operator_role == "pushes things along"
    assert cfg.autonomy.scope == ("build, test, open pull requests",)
    assert cfg.autonomy.never == ("--admin", "approving its own pull request")


def test_a_grant_without_its_bounds_is_refused() -> None:
    """A standing grant is read narrowly; one that names no `never` has no edge to read."""
    with pytest.raises(ValueError, match="never"):
        AutonomyConfig(standing_grant=True, never=())


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"standing_grant": "yes"}, "standing_grant"),
        ({"scope": ("",)}, "scope"),
        ({"never": ("a", "a")}, "never"),
        ({"operator_role": 3}, "operator_role"),
    ],
)
def test_a_malformed_grant_is_refused(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        AutonomyConfig(**kwargs)  # type: ignore[arg-type]


def test_doctor_reads_the_grant_and_the_forecast_table(tmp_path: Path) -> None:
    """Both were reported as ignored: `[autonomy]` because doctor did not know the section,
    `[estimate.forecast]` because doctor did not know the table the loader does read."""
    text = GRANT + '\n[estimate.forecast]\nledger = "x.jsonl"\nphi_floor = 0.1\n'
    messages = _messages(_write(tmp_path, text))
    assert not [m for m in messages if "autonomy" in m or "forecast" in m]


def test_doctor_still_names_a_stray_key_in_either_table(tmp_path: Path) -> None:
    text = GRANT + 'surprise = 1\n\n[estimate.forecast]\nledger = "x"\nwhatever = 2\n'
    messages = _messages(_write(tmp_path, text))
    assert any("[autonomy] surprise" in m for m in messages)
    assert any("[estimate.forecast] whatever" in m for m in messages)
