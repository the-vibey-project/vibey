# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The source distribution ships what a source build needs, and stays inside a budget.

Each push to develop uploads the wheel and the sdist to TestPyPI, which refused uploads at
its 10 GB project limit once the sdist had grown to 31 MB of documentation, generated
slices, research corpora and tests. The budget and the forbidden trees live in
``sdist_budget.toml``; this module builds the real sdist and checks it against them.
"""

from __future__ import annotations

import subprocess
import tarfile
import tomllib
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BUDGET = tomllib.loads((Path(__file__).parent / "sdist_budget.toml").read_text())
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text())
MIB = 1024 * 1024


@pytest.fixture(scope="module")
def sdist(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, int], int]:
    """The built sdist: each repository-relative path with its size, and the tarball's size."""
    out = tmp_path_factory.mktemp("sdist")
    # Built for real rather than listed through hatchling's internals: the file list in the
    # tarball is the artifact that gets uploaded, and `uv build` brings hatchling itself.
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(out), str(REPO)],
        check=True,
        capture_output=True,
    )
    (archive,) = out.glob("*.tar.gz")
    files: dict[str, int] = {}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if member.isfile():
                # Drop the leading `<name>-<version>/` directory.
                files[member.name.split("/", 1)[1]] = member.size
    return files, archive.stat().st_size


def _under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def test_sdist_ships_no_forbidden_tree(sdist: tuple[dict[str, int], int]) -> None:
    sdist_files, _ = sdist
    prefixes = BUDGET["forbidden_prefixes"] + BUDGET["ephemeral_prefixes"]
    offenders: Counter[str] = Counter()
    for path in sdist_files:
        for prefix in prefixes:
            if _under(path, prefix):
                offenders[prefix] += 1
    assert not offenders, "the sdist ships trees a source build does not need: " + ", ".join(
        f"{prefix} ({count} files)" for prefix, count in offenders.most_common()
    )


def test_sdist_is_within_budget(sdist: tuple[dict[str, int], int]) -> None:
    sdist_files, archive_size = sdist
    # The budget is the tarball, which is what TestPyPI stores and counts, not the sum of
    # the unpacked files; the trees named on failure are ranked by unpacked size.
    total = archive_size / MIB
    by_tree: Counter[str] = Counter()
    for path, size in sdist_files.items():
        by_tree[path.split("/", 1)[0]] += size
    largest = ", ".join(f"{tree} {size / MIB:.1f} MiB" for tree, size in by_tree.most_common(5))
    assert total <= BUDGET["max_total_mib"], (
        f"the sdist is {total:.1f} MiB against a budget of {BUDGET['max_total_mib']} MiB; "
        f"largest trees (unpacked): {largest}"
    )


def test_sdist_still_ships_what_the_wheel_needs(sdist: tuple[dict[str, int], int]) -> None:
    sdist_files, _ = sdist
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    needed = list(wheel["packages"]) + list(wheel["force-include"])
    missing = [src for src in needed if not any(_under(path, src) for path in sdist_files)]
    assert not missing, f"the wheel is built from paths the sdist lacks: {missing}"


def test_the_budget_has_no_unused_prefix() -> None:
    gone = [p for p in BUDGET["forbidden_prefixes"] if not (REPO / p).exists()]
    assert not gone, f"forbidden prefixes naming nothing in the repository; remove them: {gone}"
