# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release's binaries: the workflow builds what scripts/release_binaries.toml declares.

`scripts/release_binaries.py check` is the check that says out loud when the workflow, the
configuration and the downloads page have drifted apart (sub-doctrine 12.e); CI runs it
here. The rest holds the workflow's contract: it follows a successful Release on main and
can never fail it; it writes nothing until every file is built and checked, and the one job
that writes runs nothing from the tree; every action is pinned to a commit; a pull request
that changes how binaries are built exercises every builder without writing anything; and a
credential the repository lacks is said out loud and tracked, never a failed release.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "release-binaries.yml"
PAGE = "guides/downloads.md"
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def _spec() -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # `on` is the YAML 1.1 boolean `True`; safe_load gives that key, not the string.
    spec["on"] = spec.get("on", spec.get(True)) or {}
    return spec


def _run(job: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in job.get("steps", []))


def test_the_workflow_and_the_page_agree_with_the_configuration() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/release_binaries.py", "check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


def test_it_follows_a_successful_release_on_main_and_is_no_job_of_it() -> None:
    """A job of the Release run that needs an optional credential decides whether the tag
    and the docs exist at all (3.0.0 shipped without both, for want of OVSX_PAT). Building
    binaries is its own workflow, run after the release succeeded."""
    spec = _spec()
    assert spec["on"]["workflow_run"] == {
        "workflows": ["Release"],
        "types": ["completed"],
        "branches": ["main"],
    }
    assert "github.event.workflow_run.conclusion == 'success'" in spec["jobs"]["plan"]["if"]
    release = (WORKFLOWS / "vibey-engine.yml").read_text(encoding="utf-8")
    assert "release-binaries" not in release and "EXPO_TOKEN" not in release


def test_only_attach_writes_and_it_runs_nothing_from_the_tree() -> None:
    spec = _spec()
    assert spec["permissions"] == {"contents": "read"}
    writers = {
        name
        for name, job in spec["jobs"].items()
        if any(
            value == "write" and scope != "issues"
            for scope, value in (job.get("permissions") or {}).items()
        )
    }
    assert writers == {"attach", "nightly"}
    attach = spec["jobs"]["attach"]
    assert attach["if"] == "needs.plan.outputs.mode == 'publish'"
    assert attach["needs"] == ["plan", "collect"]
    uses = [step.get("uses", "") for step in attach["steps"]]
    assert not any(use.startswith("actions/checkout@") for use in uses), (
        "the job holding a write token must not check out (and so cannot run) the tree"
    )
    assert any(use.startswith("actions/attest-build-provenance@") for use in uses)
    script = _run(attach)
    assert "gh release upload" in script and "--clobber" in script
    assert "refusing to attach" in script, "it refuses a tag naming another commit"
    assert "gh release create" not in script, "the Release is github-release.yml's to create"


def test_every_action_is_pinned_to_a_commit() -> None:
    for name, job in _spec()["jobs"].items():
        for step in job.get("steps", []):
            if "uses" in step:
                assert PINNED.match(step["uses"]), f"{name}: {step['uses']} is not pinned"


def test_a_pull_request_that_changes_the_build_runs_it_as_a_dry_run() -> None:
    spec = _spec()
    paths = spec["on"]["pull_request"]["paths"]
    for path in (
        ".github/workflows/release-binaries.yml",
        "scripts/release_binaries.py",
        "scripts/release_binaries.toml",
    ):
        assert path in paths
    assert spec["on"]["workflow_dispatch"]["inputs"]["dry_run"]["default"] is True
    mode = _run(spec["jobs"]["plan"])
    assert "pull_request) mode=dry-run" in mode
    assert spec["concurrency"]["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"


def test_a_dispatched_publish_must_prove_its_commit_first() -> None:
    mode = _run(_spec()["jobs"]["plan"])
    assert "compare/${target}...${RELEASE_BRANCH}" in mode
    assert "--status success" in mode
    assert "mode=skip" in mode, "a push that bumps no version attaches nothing"


def test_a_missing_credential_is_said_and_tracked_never_a_failure() -> None:
    job = _spec()["jobs"]["app-ios"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    missing = next(step for step in job["steps"] if step.get("if") == "env.EXPO_TOKEN == ''")
    assert "::warning::" in missing["run"] and "vibey-gh tracking-issue raise" in missing["run"]
    assert "exit 1" not in missing["run"]
    build = next(step for step in job["steps"] if "eas-cli" in str(step.get("run", "")))
    assert build["if"] == "env.EXPO_TOKEN != ''"
    assert "|| true" not in build["run"], "with the credential, a failed build stays loud"


def test_the_nightly_writes_only_its_own_rolling_prerelease_and_runs_nothing_from_the_tree() -> (
    None
):
    nightly = _spec()["jobs"]["nightly"]
    assert nightly["if"] == "needs.plan.outputs.mode == 'nightly'"
    assert nightly["needs"] == ["plan", "collect"]
    uses = [step.get("uses", "") for step in nightly["steps"]]
    assert not any(use.startswith("actions/checkout@") for use in uses)
    assert any(use.startswith("actions/attest-build-provenance@") for use in uses)
    script = _run(nightly)
    assert "--prerelease --latest=false" in script  # never the release people are pointed to
    assert "git/refs/tags/${TAG}" in script  # the one tag it moves is the declared one
    assert "not the commit these files were built from" in script
    # Built from the integration branch only, and only when something it ships from changed.
    plan = _run(_spec()["jobs"]["plan"])
    assert "schedule) mode=nightly ;;" in plan
    assert "the nightly is built from $integration only" in plan
    assert "release_binaries.py nightly-due" in plan


def test_nothing_is_swallowed_in_any_build() -> None:
    for name, job in _spec()["jobs"].items():
        assert "|| true" not in _run(job), f"{name} swallows a failure"


def test_collect_waits_for_every_build_and_checksums_them() -> None:
    collect = _spec()["jobs"]["collect"]
    script = _run(collect)
    assert "release_binaries.py collect" in script
    assert "sha256sum --check --strict" in script


def test_the_downloads_page_is_in_the_guides_nav_and_linked_from_the_install_sections() -> None:
    nav = (REPO / "properdocs.yml").read_text(encoding="utf-8")
    guides = nav.split("  - Guides:", 1)[1].split("\n  - ", 1)[0]
    assert f"Downloads: {PAGE}" in guides
    assert (REPO / "docs" / PAGE).is_file()
    for document, link in (("README.md", f"docs/{PAGE}"), ("docs/index.md", PAGE)):
        text = (REPO / document).read_text(encoding="utf-8")
        install = text.split("## Install", 1)[1].split("\n## ", 1)[0]
        assert f"]({link})" in install, f"{document}'s install section does not link {link}"
