# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The committed host-health record and its page agree, and the automation around them is
wired the way the design says (sub-doctrine 12.e: the check that says out loud when a step
was missed).

`scripts/host_health.py check` is run against the tree: every line of the record is a valid
record and the page's GENERATED blocks are what the record renders to. The workflow is read
to confirm it keeps one tracking issue through `vibey-gh tracking-issue` and never measures:
the measurement runs on the host, where the hardware is visible.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
RECORD = REPO / "docs/architecture/evidence/host-health.jsonl"
WORKFLOW = REPO / ".github/workflows/host-health.yml"


def test_the_committed_record_and_page_are_in_step() -> None:
    done = subprocess.run(
        [sys.executable, "scripts/host_health.py", "check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr + done.stdout


def test_the_committed_record_carries_no_serial_number_or_host_name() -> None:
    text = RECORD.read_text(encoding="utf-8")
    for line in text.splitlines():
        raw = json.loads(line)
        assert raw["host"]["fingerprint"].startswith("sha256:")
        for forbidden in ("Serial", "IOPlatformUUID", "HostName", "ComputerName"):
            assert forbidden not in line, forbidden
    assert "MacBook-Pro" not in text, "a report name leaked the host name"


def test_every_skipped_figure_says_why() -> None:
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        for figure in json.loads(line)["figures"]:
            if figure["status"] == "skipped":
                assert figure.get("reason"), figure["id"]
                assert figure.get("value") is None, figure["id"]


def test_the_workflow_keeps_one_tracking_issue_and_never_measures() -> None:
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = spec["jobs"]["track"]["steps"]
    script = "\n".join(str(step.get("run", "")) for step in steps)
    assert "host_health.py check" in script
    assert "vibey-gh tracking-issue raise" in script and "vibey-gh tracking-issue resolve" in script
    assert "host_health.py measure" not in script and "host_health.py weekly" not in script
    assert spec["jobs"]["track"]["runs-on"] == "ubuntu-latest"
    assert spec["jobs"]["track"]["permissions"] == {"contents": "read", "issues": "write"}
