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

    assert qwen["runs"] == 8
    assert qwen["active_storm_processes"] == 2
    assert qwen["completed_runs"] == 1
    assert qwen["completion_marker_runs"] == 1
    assert qwen["verdict_runs"] == 3
    assert qwen["turns"] == 29
    assert qwen["tool_calls"] == 33
    assert qwen["input_tokens"] == 175595
    assert qwen["output_tokens"] == 23692
    assert qwen["file_write_calls"] == 13
    assert qwen["bytes_written"] == 9111
    assert qwen["empty_runs"] == 3
    assert qwen["incomplete_runs"] == 7
    assert qwen["requested_settings"]["context_length"] == 32768
    assert qwen["observed_server"]["context_length"] == 40960
