# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A placeholder left for a pending input can never ship (sub-doctrine 12.e).

The 3.0.0 update of `docs/paper.md` was written while several lanes were still in flight
(the per-device concurrency sweep, the RabbitMQ reapers, the ledger guard's review
follow-ups and the engine environment allow-list), so the paper carries a marker where
each lane's final figures belong:

    <!-- TODO(3.0.0-pending: feat/local-slot-benchmark) what goes here -->

The marker names the release it blocks and the branch it waits on, and it sits inside an
HTML comment that starts a line, so the renderer drops it from the PDF and the site never
shows it. Remembering to fill every one before the release is exactly the toil 12.e
automates, so this test does the remembering:

- **Everywhere**, every marker must be well formed: a version, a named source, inside a
  line-leading HTML comment. A malformed marker is one `grep` would miss.
- **In CI** (`CI` set, as every hosted runner sets it), any marker fails the build. The
  draft pull request that carries the markers is therefore red until the last is
  replaced, and no pull request into `develop` or `main` can merge one.
- **Once the project's version reaches a marker's version**, the marker fails the build
  wherever the suite runs: the release has happened and the placeholder is still there.
- **Otherwise** (a local run, such as the pre-push hook on the draft branch) the test is
  skipped with every pending marker named in the reason, so the push that shares the draft
  is possible and the pending work is still said out loud. `VIBEY_PENDING_GATE=1` makes a
  local run fail as CI would.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import os
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PAPER = REPO / "docs" / "paper.md"

# The strict, greppable form. Anything that looks like a pending marker but does not
# match it is refused by `test_every_pending_marker_is_well_formed`.
_MARKER = re.compile(r"TODO\((?P<version>\d+\.\d+\.\d+)-pending: (?P<source>[^)\s][^)]*)\)")
_LOOSE = re.compile(r"TODO\([^)]*-pending", re.IGNORECASE)
_TRUTHY = {"1", "true", "yes", "on"}


def _documents() -> list[Path]:
    """Every Markdown file a marker could hide in: the paper, the docs tree, the root."""
    found = {PAPER, *REPO.glob("*.md"), *(REPO / "docs").rglob("*.md")}
    return sorted(path for path in found if path.is_file())


def _markers(path: Path) -> list[tuple[int, str, str]]:
    """`(line, version, source)` for every well-formed marker in `path`."""
    out: list[tuple[int, str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for match in _MARKER.finditer(line):
            out.append((number, match["version"], match["source"].strip()))
    return out


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _project_version() -> str:
    with (REPO / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def _must_fail(marker_version: str, project_version: str, env: Mapping[str, str]) -> str | None:
    """Why a present marker fails here, or None when it may stand (skipped, and named)."""
    if _version(project_version) >= _version(marker_version):
        return f"the project is at {project_version}, and this marker blocks {marker_version}"
    if env.get("CI", "").strip().lower() in _TRUTHY:
        return "running in CI, where a pending marker never merges"
    if env.get("VIBEY_PENDING_GATE", "").strip().lower() in _TRUTHY:
        return "VIBEY_PENDING_GATE is set"
    return None


def _in_leading_comment(lines: list[str], index: int, column: int) -> bool:
    """Whether `lines[index][column]` sits in an HTML comment whose `<!--` starts a line.

    The renderer drops an HTML comment only when it opens at column 0, so a marker in a
    comment opened mid-line would be printed. Walk back from the marker to the nearest
    opener, and refuse if a closer comes between them.
    """
    before = lines[index][:column]
    if "<!--" in before:
        opener = before.rindex("<!--")
        return opener == 0 and "-->" not in before[opener:]
    if "-->" in before:
        return False
    for above in range(index - 1, -1, -1):
        text = lines[above]
        if "-->" in text:
            return False
        if "<!--" in text:
            return text.startswith("<!--")
    return False


def test_every_pending_marker_is_well_formed() -> None:
    """A marker is greppable, names its release and its source, and never reaches print."""
    problems: list[str] = []
    for path in _documents():
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if not _LOOSE.search(line):
                continue
            where = f"{path.relative_to(REPO)}:{number}"
            if not _MARKER.search(line):
                problems.append(f"{where}: not of the form TODO(X.Y.Z-pending: source)")
                continue
            if not _in_leading_comment(lines, number - 1, line.index("TODO(")):
                problems.append(f"{where}: not inside a line-leading HTML comment")
    assert not problems, "malformed pending markers:\n" + "\n".join(problems)


def test_no_pending_marker_ships() -> None:
    """While any marker remains, CI and a released version fail; a local run says so."""
    project = _project_version()
    failing: list[str] = []
    pending: list[str] = []
    for path in _documents():
        for number, version, source in _markers(path):
            where = f"{path.relative_to(REPO)}:{number} ({version}, waiting on {source})"
            reason = _must_fail(version, project, os.environ)
            if reason is None:
                pending.append(where)
            else:
                failing.append(f"{where}: {reason}")
    assert not failing, "pending placeholders must be filled before this ships:\n" + "\n".join(
        failing
    )
    if pending:
        pytest.skip("pending placeholders, which fail in CI: " + "; ".join(pending))


@pytest.mark.parametrize(
    ("marker", "project", "env", "fails"),
    [
        ("3.0.0", "2.1.0", {}, False),
        ("3.0.0", "2.1.0", {"CI": "true"}, True),
        ("3.0.0", "2.1.0", {"CI": "1"}, True),
        ("3.0.0", "2.1.0", {"CI": "false"}, False),
        ("3.0.0", "2.1.0", {"VIBEY_PENDING_GATE": "1"}, True),
        ("3.0.0", "3.0.0", {}, True),
        ("3.0.0", "3.0.1", {}, True),
        ("3.0.0", "2.99.99", {}, False),
        ("3.1.0", "3.0.0", {}, False),
    ],
)
def test_the_gate_fails_in_ci_and_after_the_release(
    marker: str, project: str, env: dict[str, str], fails: bool
) -> None:
    assert (_must_fail(marker, project, env) is not None) is fails


def test_the_marker_pattern_reads_what_the_paper_writes() -> None:
    line = "<!-- TODO(3.0.0-pending: feat/bus-reapers) the reapers' final shape -->"
    [match] = _MARKER.finditer(line)
    assert (match["version"], match["source"]) == ("3.0.0", "feat/bus-reapers")
    assert _LOOSE.search("todo(3.0.0-pending feat/x)")
    assert not _MARKER.search("todo(3.0.0-pending feat/x)")


@pytest.mark.parametrize(
    ("lines", "inside"),
    [
        (["<!-- TODO(3.0.0-pending: a) x -->"], True),
        (["<!--", "TODO(3.0.0-pending: a) x", "-->"], True),
        (["text <!-- TODO(3.0.0-pending: a) -->"], False),
        (["<!-- done -->", "TODO(3.0.0-pending: a)"], False),
        (["TODO(3.0.0-pending: a)"], False),
        (["<!-- x --> TODO(3.0.0-pending: a)"], False),
    ],
)
def test_a_marker_must_sit_in_a_comment_the_renderer_drops(lines: list[str], inside: bool) -> None:
    index = next(i for i, line in enumerate(lines) if "TODO(" in line)
    assert _in_leading_comment(lines, index, lines[index].index("TODO(")) is inside
