# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`.github/actions/vibey-state` and `vibey-state-write.yml` keep the contract ADR-0086 states.

Any workflow may open the synced state with the composite action, and only the reusable write
workflow, its one job holding `contents: write`, writes it back. The action takes every input
through `env:`, never interpolated into a script; the artifact its `close` step uploads is the
one the write workflow downloads; and its actions are pinned as `vibey-remote.yml` pins them.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from scripts import vibey_state_action as sa

REPO = Path(__file__).resolve().parents[2]
ACTION = REPO / ".github" / "actions" / "vibey-state" / "action.yml"
WRITE = REPO / ".github" / "workflows" / "vibey-state-write.yml"
REMOTE = REPO / ".github" / "workflows" / "vibey-remote.yml"
EXPRESSION = re.compile(r"\$\{\{.*?\}\}")


def load(path: Path) -> dict[Any, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def steps(path: Path) -> list[dict[str, Any]]:
    data = load(path)
    if "runs" in data:
        return list(data["runs"]["steps"])
    return [step for job in data["jobs"].values() for step in job.get("steps", [])]


def test_the_action_takes_every_input_through_env_and_interpolates_none_into_a_script() -> None:
    action = load(ACTION)
    assert action["runs"]["using"] == "composite"
    for step in action["runs"]["steps"]:
        if "run" in step:
            assert not EXPRESSION.search(step["run"]), step["name"]
            assert step["shell"] == "bash"
    run = next(s for s in action["runs"]["steps"] if s.get("id") == "state")
    passed = {value for value in run["env"].values() if "inputs." in value}
    assert passed == {f"${{{{ inputs.{name} }}}}" for name in action["inputs"]} - {
        "${{ inputs.python-version }}"
    }
    assert run["env"]["STATE_KEY"] == "${{ inputs.key }}"
    assert run["env"]["REPOSITORY_PRIVATE"] == "${{ github.event.repository.private }}"
    assert "scripts/vibey_state_action.py" in run["run"]


def test_the_action_declares_its_steps_and_outputs() -> None:
    action = load(ACTION)
    assert action["inputs"]["key"]["required"] is True
    assert action["inputs"]["token"]["default"] == "${{ github.token }}"
    assert action["inputs"]["push"]["default"] == "false"
    for name in ("opened", "state", "pushed", "artifact", "path"):
        assert action["outputs"][name]["value"] == f"${{{{ steps.state.outputs.{name} }}}}"
    script = (REPO / "scripts" / "vibey_state_action.py").read_text(encoding="utf-8")
    for step in ("open", "close", "write-back"):
        assert f'"{step}"' in script


def test_close_uploads_the_export_for_one_day_under_the_name_it_outputs() -> None:
    upload = next(
        s
        for s in load(ACTION)["runs"]["steps"]
        if str(s.get("uses", "")).startswith("actions/upload-artifact")
    )
    assert upload["if"] == "inputs.step == 'close' && steps.state.outputs.state == 'true'"
    assert upload["with"]["name"] == "${{ steps.state.outputs.artifact }}"
    assert upload["with"]["path"] == "${{ steps.state.outputs.dir }}/"
    assert upload["with"]["retention-days"] == 1
    assert upload["with"]["if-no-files-found"] == "error"


def test_the_write_workflow_is_the_one_writer_and_runs_only_the_write_back() -> None:
    write = load(WRITE)
    call = write[True]["workflow_call"]
    assert set(call["inputs"]) == {"artifact"} and call["inputs"]["artifact"]["required"]
    assert set(call["secrets"]) == {"VIBEY_STATE_KEY"}
    assert write["permissions"] == {"contents": "read"}
    [(name, job)] = write["jobs"].items()
    assert job["permissions"] == {"contents": "write"}
    assert job["concurrency"]["cancel-in-progress"] is False
    assert not any("run" in step for step in job["steps"])
    checkout = next(s for s in job["steps"] if str(s["uses"]).startswith("actions/checkout"))
    assert checkout["with"]["persist-credentials"] is False
    taken = next(s for s in job["steps"] if str(s["uses"]).startswith("actions/download-artifact"))
    assert taken["with"]["name"] == "${{ inputs.artifact }}"
    written = next(s for s in job["steps"] if s["uses"] == "./.github/actions/vibey-state")
    assert written["with"]["step"] == "write-back"
    assert written["with"]["key"] == "${{ secrets.VIBEY_STATE_KEY }}"
    # The export lands where the write-back reads it: at the artifact's root.
    assert written["with"]["file"] == f"{taken['with']['path']}/{sa.STATE_FILE}"
    # Its own database is the runner's, as the state action's owner DSN names it.
    assert written["with"]["pg-url"] == sa.EPHEMERAL_OWNER_URL
    assert job["services"]["postgres"]["env"]["POSTGRES_PASSWORD"] == "vibey"


def test_vibey_remote_hands_the_write_workflow_the_artifact_its_run_uploaded() -> None:
    jobs = load(REMOTE)["jobs"]
    handed = next(
        s
        for s in jobs["run"]["steps"]
        if str(s.get("uses", "")).startswith("actions/upload-artifact")
        and s.get("if") == "steps.command.outputs.state == 'true'"
    )
    assert jobs["sync-back"]["uses"] == "./.github/workflows/vibey-state-write.yml"
    assert jobs["sync-back"]["with"]["artifact"] == handed["with"]["name"]
    # The run's export is `state.vibey-export` at the artifact's root, as the writer reads it.
    assert handed["with"]["path"].endswith("/state/")
    assert f'"{sa.STATE_FILE}"' in (REPO / "scripts" / "vibey_state_action.py").read_text()


def test_actions_are_pinned_as_vibey_remote_pins_them() -> None:
    pinned = {
        step["uses"].split("@")[0]: step["uses"]
        for step in steps(REMOTE)
        if "uses" in step and "@" in step["uses"]
    }
    # The download half of an artifact handover is pinned as its upload half is.
    upload = pinned["actions/upload-artifact"].split("@")[1]
    pinned["actions/download-artifact"] = f"actions/download-artifact@{upload}"
    for path in (ACTION, WRITE):
        for step in steps(path):
            uses = step.get("uses", "")
            if not uses or uses.startswith("./"):
                continue
            assert uses == pinned[uses.split("@")[0]], f"{path.name}: {uses}"


def test_the_declaration_is_where_the_gate_reads_it() -> None:
    assert (REPO / sa.DECLARATION).is_file()
    assert sa.StateDeclaration(REPO / sa.DECLARATION).public() is True
