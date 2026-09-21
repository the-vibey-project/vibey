# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tracked paper evidence report includes the local Qwen storm extraction."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def test_paper_evidence_reports_qwen_storm_record() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/paper_evidence.py", "--repo", str(REPO), "--json"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    qwen = evidence["qwen_storm"]

    assert qwen["runs"] == 13
    assert qwen["active_storm_processes"] == 1
    assert qwen["completed_runs"] == 4
    assert qwen["completion_marker_runs"] == 4
    assert qwen["verdict_runs"] == 6
    assert qwen["turns"] == 105
    assert qwen["tool_calls"] == 85
    assert qwen["input_tokens"] == 550576
    assert qwen["output_tokens"] == 83609
    assert qwen["file_write_calls"] == 42
    assert qwen["bytes_written"] == 32073
    assert qwen["empty_runs"] == 4
    assert qwen["incomplete_runs"] == 9
    assert qwen["requested_settings"]["context_length"] == 32768
    assert qwen["observed_server"]["context_length"] == 40960


@pytest.mark.parametrize("active_processes", [-1, "1", True])
def test_paper_evidence_rejects_invalid_active_process_counts(
    tmp_path: Path, active_processes: object
) -> None:
    record = tmp_path / "qwen-storm.json"
    record.write_text(
        json.dumps(
            {
                "active_storm_processes_at_cutoff": active_processes,
                "runs": [],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/paper_evidence.py",
            "--repo",
            str(REPO),
            "--qwen-storm",
            str(record),
            "--json",
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert (
        "field 'active_storm_processes_at_cutoff' must be a non-negative integer" in result.stderr
    )


def test_paper_evidence_reports_zero_variance_for_one_active_day(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Paper Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "paper-test@example.invalid"], cwd=repo, check=True
    )
    (repo / "evidence.txt").write_text("one day\n", encoding="utf-8")
    subprocess.run(["git", "add", "evidence.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "test: one active day"], cwd=repo, check=True)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/paper_evidence.py"),
            "--repo",
            str(repo),
            "--stress",
            str(REPO / "src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md"),
            "--no-qwen-storm",
            "--since",
            "",
            "--json",
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    per_day = json.loads(result.stdout)["history"]["commits_per_active_day"]

    assert per_day["sd"] == 0.0
    assert per_day["cv"] == 0.0
