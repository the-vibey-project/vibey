# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""While `[version] max_major` is set in `.vibey-gh.toml`, the files below stay under that major.

The cap is the project's pre-1.0 rule. The release derivation honours it (a breaking change
bumps the minor), and this test holds these *declared* numbers to it: every version in
`[version] files`, `clients/krypton-app/pyproject.toml`, `clients/vscode/package.json` and
`packages/vibey-core/package.json`. A file above the cap must be recorded in `EXEMPT` with a
reason of at least `MIN_REASON` characters; an exemption whose file is no longer above the cap
is stale and fails. Lifting the cap (deleting `max_major`) turns the check off.

Known gaps, not checked here: the tenants that ship inside vibey-engine with their own
numbers (vibey-gh 1.73.0; vibey-bootstrap 4.2.3, which `vibey_bootstrap.__version__`
exposes), which are above the cap; and `clients/desktop/meson.build` and
`clients/app/app.config.ts`, which say 0.2.0 today but are not read. This test says nothing
about any of them.
"""

import json
import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MIN_REASON = 20

EXTRA_FILES = (
    "clients/krypton-app/pyproject.toml",
    "clients/vscode/package.json",
    "packages/vibey-core/package.json",
)

# path -> why it is allowed above the cap.
EXEMPT: dict[str, str] = {
    "clients/app/package.json": (
        "not named in the 2026-11-12 request; the operator rules whether the app moves to 0.3.0"
    ),
}

_PY_VERSION = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)
_CFF_VERSION = re.compile(r"^version:\s*['\"]?([^\s'\"#]+)", re.MULTILINE)


def read_version(path: Path) -> str:
    """The version a file declares, by its own convention."""
    text = path.read_text(encoding="utf-8")
    if path.name == "pyproject.toml":
        return str(tomllib.loads(text)["project"]["version"])
    if path.name == "package.json":
        return str(json.loads(text)["version"])
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
