# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The protected paths are declared twice, and the two declarations agree (#213).

`.github/CODEOWNERS` tells GitHub whose review a change to them needs;
`[merge_train] protected_paths` in `.vibey-gh.toml` tells the merge train never to merge
one unattended, because its `--admin` fallback would bypass that review. Either list alone
leaves a hole: a path only in CODEOWNERS is admin-merged by the train, and a path only in
the train's list merges through the merge queue with nobody's review. The single guard
before these was a regex in scripts/fleet/land.sh that drifted from what it claimed to
protect without anyone noticing, so the agreement is a test rather than a hope.

It also refuses a pattern that matches nothing tracked. A protected test that is renamed
leaves its old pattern guarding an empty set, which reads exactly like a working guard.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import subprocess
import tomllib
from fnmatch import fnmatchcase
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CODEOWNERS = REPO / ".github" / "CODEOWNERS"
CONFIG = REPO / ".vibey-gh.toml"
OWNER = "@adammatthewsteinberger"


def _codeowners() -> dict[str, list[str]]:
    """Pattern (as written) -> owners, for every non-comment line."""
    entries: dict[str, list[str]] = {}
    for line in CODEOWNERS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            pattern, *owners = stripped.split()
            entries[pattern] = owners
    return entries


def _protected_paths() -> list[str]:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    return list(config["merge_train"]["protected_paths"])


def _tracked() -> list[str]:
    listing = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return listing.splitlines()


def test_codeowners_and_the_merge_train_protect_the_same_paths() -> None:
    anchored = {pattern.removeprefix("/") for pattern in _codeowners()}
    assert anchored == set(_protected_paths())


def test_every_codeowners_pattern_is_root_anchored_and_owned_by_the_operator() -> None:
    for pattern, owners in _codeowners().items():
        assert pattern.startswith("/"), pattern
        assert owners == [OWNER], (pattern, owners)


def test_codeowners_protects_itself() -> None:
    assert "/.github/CODEOWNERS" in _codeowners()


def test_every_protected_pattern_matches_a_tracked_file() -> None:
    tracked = _tracked()
    unmatched = [
        pattern
        for pattern in _protected_paths()
        if not any(fnmatchcase(path, pattern) for path in tracked)
    ]
    assert not unmatched, f"protected patterns that match no tracked file: {unmatched}"


def test_the_no_loss_suite_is_protected() -> None:
    protected = _protected_paths()
    for suite in (
        "tests/domain/test_noloss.py",
        "tests/domain/test_noloss_reference.py",
        "tests/domain/test_briefing.py",
    ):
        assert any(fnmatchcase(suite, pattern) for pattern in protected), suite
