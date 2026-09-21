# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tracked paper evidence report includes the local Qwen storm extraction."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_paper_evidence_reports_qwen_storm_record() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/paper_evidence.py", "--repo", str(REPO), "--json"],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
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
