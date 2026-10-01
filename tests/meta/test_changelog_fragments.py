# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""This repository writes its changelogs as fragments, and nothing merges them by union.

Every pull request used to edit the same `## [Unreleased]` lines, and GitHub's mergeability
never runs the `merge=union` driver that was meant to absorb it: on 2026-10-01 #1295, #1297,
#1298 and #1299 were re-merged over and over. These hold the declaration that ended it --
both changelogs fed by fragments, the check rendered and gating, the union attribute gone --
so that losing any one of them is a red build rather than the next night of conflicts.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))


def test_both_changelogs_are_fed_by_fragments() -> None:
    changelog = CONFIG["changelog"]
    assert changelog["enabled"] is True
    assert [entry["changelog"] for entry in changelog["files"]] == [
        "CHANGELOG.md",
        "src/vibey_tools/gh/CHANGELOG.md",
    ]
    assert changelog["require_for"], "a check that requires nothing never asks for a fragment"


def test_the_check_is_rendered_and_gates_the_pull_request() -> None:
    assert "changelog.yml" in CONFIG["install"]["workflows"]
    assert (REPO / ".github" / "workflows" / "changelog.yml").is_file()
    # A gating workflow absent from scan_workflows deadlocks the PR evaluation.
    assert "Changelog" in CONFIG["pr_automation"]["scan_workflows"]


def test_neither_fragment_fed_changelog_is_merged_by_union_any_more() -> None:
    assert CONFIG["install"]["union_merge_paths"] == []
    for entry in CONFIG["changelog"]["files"]:
        changelog = Path(entry["changelog"])
        attributes = REPO / changelog.parent / ".gitattributes"
        if attributes.is_file():
            text = attributes.read_text(encoding="utf-8")
            assert f"{changelog.name} merge=union" not in text, attributes
    # And nothing in the tree still declares the root changelog a union merge.
    declared = subprocess.run(
        [
            "git",
            "check-attr",
            "merge",
            "--",
            *(e["changelog"] for e in CONFIG["changelog"]["files"]),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "union" not in declared, declared
