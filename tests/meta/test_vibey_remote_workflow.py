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


def test_only_sync_back_may_write_and_it_runs_no_dispatched_command() -> None:
    """The synced state (ADR-0086): the run reads the branch with a read-only token; the
    write-back is its own job, the only one with `contents: write`, and it runs the state
    commands alone, after the run handed it a sealed export."""
    jobs = spec()["jobs"]
    run = next(s for s in jobs["run"]["steps"] if s.get("name") == "Run the command")
    assert run["env"]["STATE_KEY"] == "${{ secrets.VIBEY_STATE_KEY }}"
    assert "--state-out" in run["run"]
    assert jobs["run"]["outputs"]["state"] == "${{ steps.command.outputs.state }}"
    handed = next(
        s for s in jobs["run"]["steps"] if s.get("name") == "Hand the sealed state to sync-back"
    )
    assert handed["if"] == "steps.command.outputs.state == 'true'"

    back = jobs["sync-back"]
    assert back["needs"] == "run" and back["if"] == "needs.run.outputs.state == 'true'"
    assert back["permissions"] == {"contents": "write"}
    assert back["concurrency"]["cancel-in-progress"] is False
    # It runs the reusable write workflow, handed the run's artifact by name, and nothing of
    # the dispatched command's.
    assert back["uses"] == "./.github/workflows/vibey-state-write.yml"
    assert back["with"] == {"artifact": handed["with"]["name"]}
    assert back["secrets"] == {"VIBEY_STATE_KEY": "${{ secrets.VIBEY_STATE_KEY }}"}
    assert "steps" not in back and "inputs." not in str(back)


def test_only_sync_back_holds_contents_write() -> None:
    """Every other job is read-only: the run job's token can read the branch, never write it."""
    writers = [
        name
        for name, job in spec()["jobs"].items()
        if "write" in (job.get("permissions") or {}).values()
    ]
    assert writers == ["sync-back"]
