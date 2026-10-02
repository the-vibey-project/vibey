# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every artifact a workflow downloads lands where its upload took it from.

`actions/upload-artifact` stores files relative to the deepest directory all its paths
share, so an upload of `docs/a/x.json` and `docs/b/y.md` holds `a/x.json` and `b/y.md`. A
download into `.` then writes them beside the tracked files instead of over them, and every
later step reads the checkout's own copies. The weekly review-canary and minimum-specs runs
did exactly that: the canary's first measurement was reported "unchanged" and lost, and the
first remeasure folded fresh Linux cells onto stale macOS figures. Nothing failed.

This test holds the rule for every workflow, so a new handover cannot repeat it silently
(sub-doctrine 12.e). A download that moves files on purpose is declared below with its reason.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import fnmatch
import posixpath
from pathlib import Path, PurePosixPath

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))

#: (workflow, artifact) -> why its download deliberately lands somewhere other than its source.
RELOCATIONS: dict[tuple[str, str], str] = {
    ("krypton-app.yml", "krypton-app-dist"): (
        "the publish jobs read `dist/`, the PyPI action's default, from a bare runner"
    ),
}


def upload_root(paths: list[str]) -> str:
    """The directory upload-artifact stores `paths` relative to: their deepest common one.

    A path naming a file contributes its parent; one naming a directory (a trailing slash,
    or no suffix) contributes itself; a glob contributes the directory before its first
    wildcard. Exclusions (`!`) never widen the root.
    """
    dirs: list[str] = []
    for raw in paths:
        path = raw.strip()
        if not path or path.startswith("!"):
            continue
        if "*" in path:
            dirs.append(posixpath.dirname(path.split("*", 1)[0]) or ".")
        elif path.endswith("/") or not PurePosixPath(path).suffix:
            dirs.append(posixpath.normpath(path))
        else:
            dirs.append(posixpath.dirname(path) or ".")
    common = posixpath.commonpath(dirs) if dirs else "."
    return common or "."


def artifact_steps(workflow: Path) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    """Every upload (artifact name -> its root) and every download step of one workflow."""
    spec = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    uploads: dict[str, list[str]] = {}
    downloads: list[dict[str, str]] = []
    for job in (spec.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            uses = str(step.get("uses", ""))
            given = {key: str(value) for key, value in (step.get("with") or {}).items()}
            if uses.startswith("actions/upload-artifact"):
                root = upload_root(given.get("path", "").splitlines())
                uploads.setdefault(given.get("name", "artifact"), []).append(root)
            elif uses.startswith("actions/download-artifact"):
                downloads.append(given)
    return uploads, downloads


def handovers() -> list[tuple[str, str, str, str]]:
    """(workflow, artifact, upload root, download destination) for every literal handover."""
    found: list[tuple[str, str, str, str]] = []
    for workflow in WORKFLOWS:
        uploads, downloads = artifact_steps(workflow)
        for download in downloads:
            destination = posixpath.normpath(download.get("path", "."))
            if "name" in download:
                names = [download["name"]] if download["name"] in uploads else []
            else:
                pattern = download.get("pattern", "*")
                names = [name for name in uploads if fnmatch.fnmatch(name, pattern)]
            for name in names:
                for root in uploads[name]:
                    if "${{" not in root + destination:
                        found.append((workflow.name, name, root, destination))
    return found


def test_upload_root_is_the_deepest_shared_directory() -> None:
    assert upload_root(["docs/a/x.json", "docs/b/y.md"]) == "docs"
    assert upload_root(["observed/forge.json"]) == "observed"
    assert upload_root(["cells/"]) == "cells"
    assert upload_root(["dist/*.whl", "dist/*.tar.gz", "!dist/skip"]) == "dist"
    assert upload_root(["README.md", "docs/x.md"]) == "."


def test_the_check_reaches_the_weekly_measurement_handovers() -> None:
    reached = {(workflow, name) for workflow, name, _, _ in handovers()}
    assert ("review-canary.yml", "review-canary") in reached
    assert ("minimum-specs.yml", "minimum-specs") in reached


@pytest.mark.parametrize(
    ("workflow", "artifact", "root", "destination"),
    handovers(),
    ids=lambda value: str(value),
)
def test_every_download_lands_where_its_upload_took_the_files_from(
    workflow: str, artifact: str, root: str, destination: str
) -> None:
    if (workflow, artifact) in RELOCATIONS:
        return
    assert destination == root, (
        f"{workflow}: artifact {artifact!r} holds files relative to {root!r}, but is "
        f"downloaded into {destination!r}, so they land beside the files they replace. "
        f"Download into {root!r}, or declare the move in RELOCATIONS with its reason."
    )


def test_every_declared_relocation_still_exists() -> None:
    present = {(workflow, name) for workflow, name, _, _ in handovers()}
    assert set(RELOCATIONS) <= present
