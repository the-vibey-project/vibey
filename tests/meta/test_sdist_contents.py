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
import zipfile
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BUDGET = tomllib.loads((Path(__file__).parent / "sdist_budget.toml").read_text())
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text())
MIB = 1024 * 1024


@pytest.fixture(scope="module")
def sdist_archive(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The built sdist tarball."""
    out = tmp_path_factory.mktemp("sdist")
    # Built for real rather than listed through hatchling's internals: the file list in the
    # tarball is the artifact that gets uploaded, and `uv build` brings hatchling itself.
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(out), str(REPO)],
        check=True,
        capture_output=True,
    )
    (archive,) = out.glob("*.tar.gz")
    return archive


@pytest.fixture(scope="module")
def sdist(sdist_archive: Path) -> tuple[dict[str, int], int]:
    """The sdist's contents: each repository-relative path with its size, and the tarball's size."""
    archive = sdist_archive
    files: dict[str, int] = {}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if member.isfile():
                # Drop the leading `<name>-<version>/` directory.
                files[member.name.split("/", 1)[1]] = member.size
    return files, archive.stat().st_size


@pytest.fixture(scope="module")
def wheel_names(sdist_archive: Path, tmp_path_factory: pytest.TempPathFactory) -> list[str]:
    """The names inside the wheel built FROM the sdist, as the release workflows build it
    (`python -m build` makes the sdist, then the wheel from that sdist): a build hook that
    reads a file the sdist dropped fails here and not in Release."""
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(out), str(sdist_archive)],
        check=True,
        capture_output=True,
    )
    (wheel,) = out.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


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


def _tree(path: str) -> str:
    """The tree a file counts toward: three segments under src/, else the first segment."""
    parts = path.split("/")
    depth = 3 if parts[0] == "src" else 1
    return "/".join(parts[:depth]) if len(parts) > depth else path


def _budget_message(files: dict[str, int], archive_size: int) -> str:
    # The budget is the tarball, which is what TestPyPI stores and counts. A tar listing
    # carries no per-file compressed size, so the trees are ranked by unpacked size.
    by_tree: Counter[str] = Counter()
    for path, size in files.items():
        by_tree[_tree(path)] += size
    largest = ", ".join(f"{tree} {size / MIB:.1f} MiB" for tree, size in by_tree.most_common(5))
    return (
        f"the sdist is {archive_size / MIB:.1f} MiB against a budget of "
        f"{BUDGET['max_total_mib']} MiB; largest trees (ranked by unpacked size, "
        f"not compressed): {largest}"
    )


def test_sdist_is_within_budget(sdist: tuple[dict[str, int], int]) -> None:
    sdist_files, archive_size = sdist
    assert archive_size / MIB <= BUDGET["max_total_mib"], _budget_message(sdist_files, archive_size)


def test_budget_failure_names_the_nested_tree() -> None:
    synthetic = {
        "pyproject.toml": 2_000,
        "src/vibey/cli/main.py": 1 * MIB,
        "src/vibey_tools/gh/assets/blob.bin": 20 * MIB,
        "src/vibey_tools/skills/plugins/x.md": 2 * MIB,
    }
    message = _budget_message(synthetic, 30 * MIB)
    assert "src/vibey_tools/gh 20.0 MiB" in message
    assert message.index("src/vibey_tools/gh") < message.index("src/vibey_tools/skills")
    assert "src 2" not in message  # never the bare `src` bucket


def test_sdist_still_ships_what_the_wheel_needs(sdist: tuple[dict[str, int], int]) -> None:
    sdist_files, _ = sdist
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    needed = list(wheel["packages"]) + list(wheel["force-include"])
    missing = [src for src in needed if not any(_under(path, src) for path in sdist_files)]
    assert not missing, f"the wheel is built from paths the sdist lacks: {missing}"


def test_the_budget_has_no_unused_prefix() -> None:
    gone = [p for p in BUDGET["forbidden_prefixes"] if not (REPO / p).exists()]
    assert not gone, f"forbidden prefixes naming nothing in the repository; remove them: {gone}"


def test_a_wheel_builds_from_the_sdist_and_carries_the_packages(wheel_names: list[str]) -> None:
    assert "vibey/__init__.py" in wheel_names
    assert "vibey_gh/__init__.py" in wheel_names
