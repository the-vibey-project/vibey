# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every test file in the repository sits where some suite actually collects it.

A test file pytest never collects is worse than no test file: it reads like coverage, it
is edited alongside the code it tests, and it goes green on every CI run because CI never
runs it. `docs/plans/qwenstorm-3.0.0/tools/test_lane_publish.py` carried 30 tests of the
storm's check parser that way. The root's `testpaths = ["tests"]` never reached it, no
workflow or hook named it, and it ran only when somebody remembered to run it by hand.

Remembering is the step sub-doctrine 12.e says to stop depending on. Where a step cannot be
made whole, the check that says out loud when it was missed is automated. This is that
check. It names every stray file, so the fix is obvious: move the file into a collected
location, or delete it if it duplicates one.

WHAT COUNTS AS COLLECTED
------------------------
The root's own `testpaths`, plus each workspace tenant's, because every tenant runs its own
suite from its own directory (ADR-0022). Both are READ from the configuration: the tenant
list from the root's `[tool.uv.workspace] members` globs, and each tenant's test locations
from its own `[tool.pytest.ini_options]` (or `pytest.ini`). Nothing here is compiled in
(12.h), so a new tenant or a moved suite is judged by what it declares. A tenant that
declares no `testpaths` is collected from its root, which is what pytest does without one.
The file's name must also match the governing `python_files`: a file inside `tests/` that
pytest skips by name never runs either.

Only tracked files are judged, because only tracked files reach CI. Virtualenv and vendored
trees are excluded because they are not this repository's tests.
"""

from __future__ import annotations

import configparser
import fnmatch
import subprocess
import tomllib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = ("test_*.py", "*_test.py")  # pytest's default `python_files`
# Path components that mark a tree as somebody else's code, never this repository's tests.
FOREIGN = {"site-packages", "node_modules", "vendor", "_vendor", "vendored", "venv", ".venv"}


def ini_options(project: Path) -> dict | None:
    """A project's pytest settings, from `pyproject.toml` or `pytest.ini`, or None."""
    pyproject = project / "pyproject.toml"
    if pyproject.is_file():
        found = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        options = found.get("tool", {}).get("pytest", {}).get("ini_options")
        if options is not None:
            return options
    ini = project / "pytest.ini"
    if ini.is_file():
        parser = configparser.ConfigParser()
        parser.read(ini, encoding="utf-8")
        if parser.has_section("pytest"):
            return {k: v.split() for k, v in parser.items("pytest")}
    return None


def suites() -> list[tuple[PurePosixPath, list[PurePosixPath], tuple[str, ...]]]:
    """Every suite: its project root, its collected directories, and its file patterns."""
    root_config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    projects = [ROOT]
    for pattern in root_config["tool"]["uv"]["workspace"]["members"]:
        projects += sorted(p for p in ROOT.glob(pattern) if (p / "pyproject.toml").is_file())
    out = []
    for project in projects:
        options = ini_options(project) or {}
        base = PurePosixPath(project.relative_to(ROOT).as_posix())
        paths = [base / p for p in options.get("testpaths", [])] or [base]
        patterns = tuple(options.get("python_files", TEST_FILE))
        out.append((base, paths, patterns))
    return out


def tracked_test_files() -> list[PurePosixPath]:
    done = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    # Not a skip: a guard that quietly stops guarding is the failure this file exists for.
    assert done.returncode == 0, f"cannot list tracked files: {done.stderr.strip()}"
    files = [PurePosixPath(p) for p in done.stdout.split("\0") if p]
    return [
        f
        for f in files
        if any(fnmatch.fnmatch(f.name, p) for p in TEST_FILE)
        and not FOREIGN & set(f.parts)
        and not any(part.startswith(".venv") for part in f.parts)
    ]


def governing(
    path: PurePosixPath, all_suites: list[tuple[PurePosixPath, list[PurePosixPath], tuple]]
):
    """The innermost suite whose project contains `path` -- a tenant's own, before the root's."""
    owners = [s for s in all_suites if s[0] == PurePosixPath(".") or s[0] in path.parents]
    return max(owners, key=lambda s: len(s[0].parts) if s[0] != PurePosixPath(".") else 0)


def strays() -> list[str]:
    all_suites = suites()
    out = []
    for path in tracked_test_files():
        _, collected, patterns = governing(path, all_suites)
        inside = any(c == PurePosixPath(".") or c in path.parents for c in collected)
        named = any(fnmatch.fnmatch(path.name, p) for p in patterns)
        if not inside:
            out.append(
                f"{path} -- outside every collected location ({', '.join(map(str, collected))})"
            )
        elif not named:
            out.append(f"{path} -- its name matches none of python_files {list(patterns)}")
    return out


def test_every_test_file_is_collected_by_some_suite() -> None:
    found = strays()
    assert not found, (
        "these test files are never collected, so their tests never run in CI -- move each "
        "into a collected location, or delete it if it duplicates one:\n  " + "\n  ".join(found)
    )


def test_the_guard_sees_the_suites_it_is_meant_to() -> None:
    """If the configuration reading broke, the guard would pass by seeing nothing."""
    all_suites = suites()
    assert (PurePosixPath("."), [PurePosixPath("tests")], TEST_FILE) in all_suites
    assert len(all_suites) > 1, "no workspace tenant was read"
    assert len(tracked_test_files()) > 100, "the tracked test files were not listed"


def test_a_stray_file_is_reported_by_name(monkeypatch) -> None:
    """The guard itself: a test file outside every suite is named, not counted."""
    stray = PurePosixPath("docs/somewhere/test_forgotten.py")
    real = tracked_test_files()
    monkeypatch.setitem(globals(), "tracked_test_files", lambda: [*real, stray])
    assert any(line.startswith(str(stray)) for line in strays())
