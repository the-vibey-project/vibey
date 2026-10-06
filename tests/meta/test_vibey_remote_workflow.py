# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`.github/workflows/vibey-remote.yml` keeps the contract `vibey -w` reads it by (ADR-0085).

The adapter finds a run by its name and reads its report from one artifact; the workflow runs a
command line a caller sent, so it must take it through `env:` only, run it as an argument
vector, and hold no write permission.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from vibey.domain.remote_command import RemoteCommand
from vibey.infrastructure.workflows.gh_workflows import RESULT_ARTIFACT, RESULT_FILE

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "vibey-remote.yml"


def spec() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_the_run_is_named_as_the_adapter_finds_it() -> None:
    assert spec()["run-name"] == "vibey ${{ inputs.request }}"
    assert RemoteCommand.run_name_for("0123456789abcdef") == "vibey 0123456789abcdef"


def test_it_takes_exactly_the_inputs_the_adapter_sends() -> None:
    inputs = spec()[True]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"request", "argv"}
    assert all(field["required"] for field in inputs.values())


def test_the_report_is_the_artifact_the_adapter_downloads() -> None:
    job = spec()["jobs"]["run"]
    upload = next(
        s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/upload-artifact")
    )
    assert upload["with"]["name"] == RESULT_ARTIFACT
    assert upload["if"] == "always()"
    runner = (Path(__file__).resolve().parents[2] / "scripts" / "vibey_remote.py").read_text()
    assert f'"{RESULT_FILE}"' in runner


def test_the_command_line_arrives_through_env_and_nothing_can_write() -> None:
    data = spec()
    assert data["permissions"] == {"contents": "read"}
    job = data["jobs"]["run"]
    assert job["permissions"] == {"contents": "read"}
    assert job["runs-on"] == "ubuntu-latest"
    for step in job["steps"]:
        assert "inputs." not in str(step.get("run", "")), step.get("name")
    run = next(s for s in job["steps"] if s.get("name") == "Run the command")
    assert run["env"]["ARGV"] == "${{ inputs.argv }}"
    assert run["run"].startswith("python scripts/vibey_remote.py run")
    checkout = next(
        s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["persist-credentials"] is False
