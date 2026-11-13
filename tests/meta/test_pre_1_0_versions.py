# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""While `[version] max_major` is set in `.vibey-gh.toml`, every declared version stays under that major.

The cap is the project's pre-1.0 rule. The release derivation honours it (a breaking change
bumps the minor), and this test holds every *declared* number to it: each version in
`[version] files`, plus every package and client the repository versions on its own: the
four runners, vibey-gh, vibey-bootstrap, vibey-skills, krypton-app, the VS Code extension,
the krypton mobile and web app, the desktop client and `@vibey/core`, in the manifest, the
module constant or the lock entry that carries each one. A file above the cap must be
recorded in `EXEMPT` with a reason of at least `MIN_REASON` characters; an exemption whose
file is no longer above the cap is stale and fails. Lifting the cap (deleting `max_major`)
turns the check off.

Changelogs and migration guides are history and keep the numbers they were written at.
"""

import json
import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MIN_REASON = 20

# A path may carry a `#a>b>c` suffix: the key path into a JSON file (`>` separates keys, for
# the lock entries named `packages/vibey-core`), for the lock entries a package-lock.json keeps
# beside the manifest.
EXTRA_FILES = (
    "clients/krypton-app/pyproject.toml",
    "clients/vscode/package.json",
    "packages/vibey-core/package.json",
    "clients/app/package.json",
    "clients/app/package-lock.json#version",
    "clients/app/package-lock.json#packages>>version",
    "clients/app/app.config.ts",
    "clients/desktop/meson.build",
    "package-lock.json#packages>packages/vibey-core>version",
    "package-lock.json#packages>clients/vscode>version",
    "src/vibey_runners/claude/pyproject.toml",
    "src/vibey_runners/claude/src/claudeloop/__init__.py",
    "src/vibey_runners/codex/pyproject.toml",
    "src/vibey_runners/codex/src/codexloop/__init__.py",
    "src/vibey_runners/common/pyproject.toml",
    "src/vibey_runners/qwen/pyproject.toml",
    "src/vibey_runners/qwen/src/qwenloop/__init__.py",
    "src/vibey_tools/bootstrap/pyproject.toml",
    "src/vibey_tools/bootstrap/vibey_bootstrap/__init__.py",
    "src/vibey_tools/gh/pyproject.toml",
    "src/vibey_tools/gh/vibey_gh/__init__.py",
    "src/vibey_tools/skills/src/vibey_skills/__init__.py",
    "src/vibey_tools/skills/.claude-plugin/marketplace.json#metadata>version",
)

# path -> why it is allowed above the cap. Empty: nothing is.
EXEMPT: dict[str, str] = {}

_PY_VERSION = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)
_CFF_VERSION = re.compile(r"^version:\s*['\"]?([^\s'\"#]+)", re.MULTILINE)
_TS_VERSION = re.compile(r"^\s+version:\s*'([^']+)',", re.MULTILINE)
_MESON_VERSION = re.compile(r"project\([^)]*?version:\s*'([^']+)'", re.DOTALL)


def read_version(spec: Path) -> str:
    """The version a file declares, by its own convention."""
    file_part, _, key_path = str(spec).partition("#")
    path = Path(file_part)
    text = path.read_text(encoding="utf-8")
    if key_path:
        node = json.loads(text)
        for key in key_path.split(">"):
            node = node[key]
        return str(node)
    if path.name == "pyproject.toml":
        return str(tomllib.loads(text)["project"]["version"])
    if path.name == "package.json":
        return str(json.loads(text)["version"])
    if path.name == "meson.build":
        pattern = _MESON_VERSION
    elif path.suffix == ".ts":
        pattern = _TS_VERSION
    else:
        pattern = _PY_VERSION if path.suffix == ".py" else _CFF_VERSION
    match = pattern.search(text)
    assert match is not None, f"{path}: no version found"
    return match.group(1)


def major(version: str) -> int:
    return int(version.split(".")[0])


def violations(
    versions: dict[str, str], max_major: int | None, exempt: dict[str, str]
) -> list[str]:
    """Problems for a {path: version} map under a cap; empty when the cap is lifted."""
    if max_major is None:
        return []
    problems = []
    for path, version in sorted(versions.items()):
        above = major(version) > max_major
        if path in exempt:
            if len(exempt[path].strip()) < MIN_REASON:
                problems.append(f"{path}: exemption reason shorter than {MIN_REASON} characters")
            if not above:
                problems.append(f"{path}: stale exemption, {version} is within the cap")
        elif above:
            problems.append(f"{path}: {version} exceeds max_major {max_major}")
    return problems


def _declared_versions() -> tuple[dict[str, str], int | None]:
    table = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))["version"]
    paths = [*table["files"], *EXTRA_FILES, *EXEMPT]
    return {p: read_version(REPO / p) for p in paths}, table.get("max_major")


def test_every_declared_version_respects_max_major() -> None:
    versions, max_major = _declared_versions()
    assert violations(versions, max_major, EXEMPT) == []


@pytest.mark.parametrize(
    ("versions", "exempt", "fragment"),
    [
        ({"a": "1.0.0"}, {"a": "x" * 19}, "shorter than"),
        ({"a": "0.3.0"}, {"a": "x" * 30}, "stale exemption"),
        ({"a": "1.0.0"}, {}, "exceeds max_major"),
    ],
)
def test_a_stale_or_unexplained_exemption_fails(
    versions: dict[str, str], exempt: dict[str, str], fragment: str
) -> None:
    assert any(fragment in p for p in violations(versions, 0, exempt))


def test_max_major_lifted_means_no_check() -> None:
    assert violations({"a": "4.6.0"}, None, {}) == []
    assert violations({"a": "0.3.0"}, 0, {}) == []


def test_the_vscode_extension_pins_the_core_it_ships_with() -> None:
    """The extension depends on `@vibey/core` by exact version, so it must name this one."""
    core = read_version(REPO / "packages/vibey-core/package.json")
    pinned = json.loads((REPO / "clients/vscode/package.json").read_text(encoding="utf-8"))
    assert pinned["devDependencies"]["@vibey/core"] == core


@pytest.mark.parametrize(
    ("manifest", "constant"),
    [
        (
            "src/vibey_tools/gh/pyproject.toml",
            "src/vibey_tools/gh/vibey_gh/__init__.py",
        ),
        (
            "src/vibey_tools/bootstrap/pyproject.toml",
            "src/vibey_tools/bootstrap/vibey_bootstrap/__init__.py",
        ),
        (
            "clients/app/package.json",
            "clients/app/app.config.ts",
        ),
        # The runners assert this themselves in their own suites (codexloop's
        # tests/test_packaging.py), but those run only in the tenant CI jobs, after a merge;
        # a stale constant reached develop that way once (the 0.3.0 move missed codexloop's).
        (
            "src/vibey_runners/claude/pyproject.toml",
            "src/vibey_runners/claude/src/claudeloop/__init__.py",
        ),
        (
            "src/vibey_runners/codex/pyproject.toml",
            "src/vibey_runners/codex/src/codexloop/__init__.py",
        ),
        (
            "src/vibey_runners/qwen/pyproject.toml",
            "src/vibey_runners/qwen/src/qwenloop/__init__.py",
        ),
        ("pyproject.toml", "src/vibey/__init__.py"),
    ],
)
def test_a_manifest_and_the_constant_that_exposes_it_agree(manifest: str, constant: str) -> None:
    assert read_version(REPO / manifest) == read_version(REPO / constant)
