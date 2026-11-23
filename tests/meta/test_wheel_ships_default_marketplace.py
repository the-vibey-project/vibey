# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The published wheel carries the default marketplace as a marketplace root, and code imported
from the wheel finds it (SP-LOOPS Task 6, Step 4; design Decision 1).

Measured on 2026-11-23: a wheel built from develop carried the `currency-research` plugin at
`vibey_skills/plugins/` but its manifest at `vibey_skills/marketplace.json`, outside any
`.claude-plugin/` folder. `MarketplaceManifest` reads `<root>/.claude-plugin/marketplace.json`, so
no folder in an installed wheel was a marketplace it could read, and the shipped marketplace could
not lock itself. Using `vibey_skills/` itself as the root would not do either: it is a Python
package, and the `__pycache__` an import writes there would change the locked digest after the
first run. So the wheel ships one folder that holds the marketplace and nothing else,
`vibey_skills/marketplace/` (`.claude-plugin/marketplace.json` and `plugins/`), moved rather than
copied so the wheel carries one copy of the 15 MiB tree.

Like tests/meta/test_wheel_ships_migrations.py, this builds the real wheel -- the artifact PyPI
receives -- once for the module, and asserts on its file list and on code run from its unpacked
contents. The build reads only this checkout and uv's cache: `uv build --offline` takes the build
backend from the cache `uv sync` filled and never asks a package index (without `--offline`, uv
resolves hatchling against the index even with a warm cache). The assertions depend on no file
order or timing.

Module-level test functions rather than a class with an interface beside it (ADR-0016), following
tests/meta/test_shipped_trees_are_reachable.py: pytest collects `test_*` functions, and the rule is
about production code.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.defaults import (
    DEFAULT_MARKETPLACE_NAME,
    DEFAULT_RESEARCH_PLUGINS,
)
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.resolver import CapabilityResolver

REPO = Path(__file__).resolve().parents[2]
TENANT = REPO / "src" / "vibey_tools" / "skills"
ROOT = "vibey_skills/marketplace"
MANIFEST = f"{ROOT}/.claude-plugin/marketplace.json"
RESEARCH_SKILLS = {
    "research-search-and-source-quality",
    "research-currency-audit-method",
    "research-editing-a-reference-skill",
}

SHIPPED_SOURCE = "vibey-engine 0.0.0+meta-test"

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The wheel `uv build --offline` produces from this checkout, built once for the module.

    Offline: the build backend (hatchling) comes from uv's cache, which `uv sync` filled, so the
    build never asks a package index (no test may need the network)."""
    uv = shutil.which("uv")
    assert uv is not None, "uv is not on PATH; the release builds the wheel with it"
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(  # noqa: S603 -- a fixed argv; uv's path comes from shutil.which
        [uv, "build", "--wheel", "--offline", "--out-dir", str(out), str(REPO)],
        check=True,
        capture_output=True,
        text=True,
    )
    built = sorted(out.glob("vibey_engine-*.whl"))
    assert len(built) == 1, f"expected one vibey_engine wheel, found {built}"
    return built[0]


@pytest.fixture(scope="module")
def names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


@pytest.fixture(scope="module")
def unpacked(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("site-packages")
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(site)
    return site


def _source_plugin(name: str) -> list[str]:
    plugin = TENANT / "plugins" / name
    files = sorted(
        path.relative_to(TENANT).as_posix()
        for path in plugin.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    assert files, f"no files in {plugin}; the tree moved and this test did not"
    return files


def test_the_wheel_carries_the_marketplace_manifest_where_a_marketplace_has_it(
    names: list[str], wheel: Path
) -> None:
    assert MANIFEST in names
    with zipfile.ZipFile(wheel) as archive:
        shipped = archive.read(MANIFEST)
    assert shipped == (TENANT / ".claude-plugin" / "marketplace.json").read_bytes()


@pytest.mark.parametrize("plugin", DEFAULT_RESEARCH_PLUGINS)
def test_the_wheel_carries_every_file_of_the_default_research_plugins(
    names: list[str], plugin: str
) -> None:
    shipped = {name for name in names if name.startswith(f"{ROOT}/plugins/{plugin}/")}
    assert shipped == {f"{ROOT}/{path}" for path in _source_plugin(plugin)}


def test_the_marketplace_root_holds_the_marketplace_and_nothing_else(names: list[str]) -> None:
    """No Python package lives in the locked tree, so no import writes `__pycache__` into it."""
    top = {name.removeprefix(f"{ROOT}/").split("/")[0] for name in names if name.startswith(ROOT)}
    assert top == {".claude-plugin", "plugins"}


def test_the_wheel_carries_one_copy_of_the_plugins_tree(names: list[str]) -> None:
    skill_files = [name for name in names if name.endswith("/SKILL.md")]
    source = list((TENANT / "plugins").glob("*/skills/*/SKILL.md"))
    assert len(skill_files) == len(source)
    assert all(name.startswith(f"{ROOT}/plugins/") for name in skill_files)
    assert "vibey_skills/marketplace.json" not in names


def test_the_default_bundle_resolves_from_the_unpacked_wheel(
    unpacked: Path, tmp_path: Path
) -> None:
    """A fresh install has the research skills with no network: the shipped copy locks itself."""
    resolver = CapabilityResolver(
        tmp_path / "loops.lock", tmp_path / "snapshots", shipped_source=SHIPPED_SOURCE
    )
    snapshot = resolver.resolve(
        BundleSpec.default(), (), {DEFAULT_MARKETPLACE_NAME: unpacked / ROOT}
    )
    assert {skill.name for skill in snapshot.skills.skills} >= RESEARCH_SKILLS
    assert all(not path.is_relative_to(unpacked) for path in snapshot.plugin_dirs)


def test_code_imported_from_the_wheel_finds_the_marketplace(unpacked: Path, tmp_path: Path) -> None:
    """The locators, run from the wheel's layout rather than from `src/`.

    The wheel is unpacked and put first on `PYTHONPATH`, so `vibey_skills` and `vibey` import
    from it and the third-party dependencies still come from this environment. Had a locator
    fallen back to the checkout, its answer would not be inside `unpacked`.
    """
    probe = (
        "import json, vibey_skills\n"
        "from vibey.infrastructure.mcp.llm_tooling_probe import LlmToolingProbe\n"
        "print(json.dumps({\n"
        "    'root': str(vibey_skills.marketplace_root()),\n"
        "    'plugins': str(vibey_skills.plugins_root()),\n"
        "    'manifest': str(vibey_skills.marketplace_manifest_path()),\n"
        "    'skill': str(LlmToolingProbe.shipped_skill()),\n"
        "}))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(unpacked)}
    result = subprocess.run(  # noqa: S603 -- a fixed argv: this interpreter and a literal probe
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    found = {key: Path(value) for key, value in json.loads(result.stdout).items()}

    root = (unpacked / ROOT).resolve()
    assert found["root"].resolve() == root
    assert found["plugins"].resolve() == root / "plugins"
    assert found["manifest"].resolve() == (unpacked / MANIFEST).resolve()
    assert found["skill"].resolve().is_relative_to(root / "plugins")


def test_a_checkout_and_the_wheel_lock_the_shipped_marketplace_alike(
    unpacked: Path, tmp_path: Path
) -> None:
    """The shipped lock covers the manifest and the plugin folders it lists, never bytecode: the
    lock a source checkout writes (its marketplace folder also holds sources and tests) is the
    lock an installed wheel matches, so moving between them is no `LockMismatchError`."""
    lock_path = tmp_path / "loops.lock"
    resolver = CapabilityResolver(lock_path, tmp_path / "snapshots", shipped_source=SHIPPED_SOURCE)
    resolver.resolve(BundleSpec.default(), (), {DEFAULT_MARKETPLACE_NAME: TENANT})
    locked = CapabilityLock().read(lock_path)
    resolver.resolve(BundleSpec.default(), locked, {DEFAULT_MARKETPLACE_NAME: unpacked / ROOT})
    assert CapabilityLock().read(lock_path) == locked  # matched, so nothing was locked again
