# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibey_gh.cli import _forecast_state, main
from vibey_gh.feasibility import StateVector


def _scripted_forecast_gh(fake_gh) -> None:
    fake_gh.script(
        {
            "issue list --repo owner/repo --state all --limit 1000 --json number,state,labels": {
                "out": json.dumps([{"number": 1, "state": "OPEN", "labels": []}])
            },
            "pr list --repo owner/repo --state all --limit 1000 --json number,state,mergedAt,labels": {
                "out": json.dumps(
                    [
                        {
                            "number": 2,
                            "state": "MERGED",
                            "mergedAt": "2026-09-18T00:00:00Z",
                            "labels": [],
                        }
                    ]
                )
            },
        }
    )


def test_forecast_cli_records_report_json_and_step_summary(
    tmp_path: Path, monkeypatch, capsys, fake_gh
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text(
        '[platform]\nrepository = "owner/repo"\n', encoding="utf-8"
    )
    _scripted_forecast_gh(fake_gh)
    billing = tmp_path / "billing.jsonl"
    billing.write_text(
        json.dumps(
            {
                "kind": "BudgetSpent",
                "produced_at": "2026-09-18T00:00:00Z",
                "payload": {"dollars": 2.0, "turns": 1},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    materials = tmp_path / "materials.json"
    materials.write_text(
        json.dumps(
            [
                {"coordinate": "agency.reliability", "value": 0.8, "source": "test"},
                {"coordinate": "hardware.availability", "value": None, "measured_at": 3},
            ]
        ),
        encoding="utf-8",
    )
    estimate_path = tmp_path / "estimates.jsonl"
    report_path = tmp_path / "estimate.md"
    summary_path = tmp_path / "summary.md"
    assert (
        main(
            [
                "forecast",
                "--record",
                str(estimate_path),
                "--report",
                str(report_path),
                "--summary",
                str(summary_path),
                "--billing-ledger",
                str(billing),
                "--materials",
                str(materials),
                "--json",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"schema": "vibey-delivery-forecast/v1"' in output
    assert estimate_path.is_file() and report_path.is_file() and summary_path.is_file()

    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "env-summary.md"))
    assert main(["forecast", "--no-record", "--no-report", "--strict"]) == 1
    assert (tmp_path / "env-summary.md").is_file()
    monkeypatch.delenv("GITHUB_STEP_SUMMARY")
    assert main(["forecast", "--no-record", "--no-report"]) == 0
    assert main(["forecast", "--limit", "0", "--no-record", "--no-report"]) == 1


def test_forecast_state_accepts_object_form_and_rejects_bad_rows(tmp_path: Path) -> None:
    path = tmp_path / "materials.json"
    path.write_text(
        json.dumps(
            {"materials": [{"coordinate": "agency.reliability", "value": 0.5, "measured_at": 2}]}
        ),
        encoding="utf-8",
    )
    state = _forecast_state(path)
    assert isinstance(state, StateVector)
    assert state.measured == 1
    assert _forecast_state(None).measured == 0

    for value, message in (
        ({"materials": "bad"}, "materials input"),
        ({"materials": ["bad"]}, "each material"),
        ({"materials": [{"coordinate": "bad"}]}, "coordinate"),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises((TypeError, ValueError), match=message):
            _forecast_state(path)
