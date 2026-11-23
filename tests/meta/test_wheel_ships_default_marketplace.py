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

from tests.meta.wheel_artifact import build_wheel, unpack

REPO = Path(__file__).resolve().parents[2]
TENANT = REPO / "src" / "vibey_tools" / "skills"
PACKAGED = TENANT / "packaged" / "marketplace.json"
ROOT_MANIFEST = REPO / ".claude-plugin" / "marketplace.json"
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
    build never asks a package index (no test may need the network); a cold cache skips with
    the command that warms it, and any other failure shows uv's stderr
    (tests/meta/wheel_artifact.py)."""
    return build_wheel(REPO, tmp_path_factory.mktemp("wheel"))


@pytest.fixture(scope="module")
def names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as archive:
        return archive.namelist()


@pytest.fixture(scope="module")
def unpacked(wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The wheel unpacked with each file's recorded mode, as an installer leaves it."""
    return unpack(wheel, tmp_path_factory.mktemp("site-packages"))


def _source_plugin(name: str) -> list[str]:
    plugin = TENANT / "plugins" / name
    files = sorted(
        path.relative_to(TENANT).as_posix()
        for path in plugin.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    assert files, f"no files in {plugin}; the tree moved and this test did not"
    return files


def test_the_wheel_manifest_is_the_packaged_rendering(names: list[str], wheel: Path) -> None:
    """The manifest a marketplace reads is the packaged rendering of the root one (Phase 3c)."""
    assert MANIFEST in names
    with zipfile.ZipFile(wheel) as archive:
        shipped = archive.read(MANIFEST)
    assert shipped == PACKAGED.read_bytes()


def test_the_wheel_carries_every_root_plugin_with_its_plugin_json(names: list[str]) -> None:
    root = json.loads(ROOT_MANIFEST.read_text(encoding="utf-8"))
    assert root["plugins"], "the root manifest lists no plugin"
    present = set(names)
    for plugin in root["plugins"]:
        folder = Path(plugin["source"]).name
        assert f"{ROOT}/plugins/{folder}/.claude-plugin/plugin.json" in present, plugin["name"]


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
    source = [
        *(TENANT / "plugins").glob("*/skills/*/SKILL.md"),
        *(REPO / "src" / "vibey_tools" / "gh" / "plugins").glob("*/skills/*/SKILL.md"),
    ]
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


def test_the_wheel_locks_the_same_plugin_files_a_checkout_locks(
    unpacked: Path, tmp_path: Path
) -> None:
    """The shipped lock covers the manifest and the plugin folders it lists, never bytecode.

    Since Phase 3c a checkout locks the repository root's manifest, whose sources name each
    member's folder, while the wheel's packaged manifest names `./plugins/<folder>`; the two
    manifests differ in their sources, so their digests differ and a person who moves between
    a checkout and an install of the same release re-locks with `vibey loops lock` (recorded in
    the Phase 3c ledger). What must not differ is the plugin content: every plugin file the
    wheel locks is byte for byte the file the checkout locks.
    """
    locker = CapabilityLock()
    resolver = CapabilityResolver(
        tmp_path / "loops.lock", tmp_path / "snapshots", shipped_source=SHIPPED_SOURCE
    )
    checkout = {
        r.path: r
        for r in locker.tree_records(REPO, resolver._shipped_scope(DEFAULT_MARKETPLACE_NAME, REPO))  # noqa: SLF001
    }
    wheel_root = unpacked / ROOT
    wheel = {
        r.path: r
        for r in locker.tree_records(
            wheel_root,
            resolver._shipped_scope(DEFAULT_MARKETPLACE_NAME, wheel_root),  # noqa: SLF001
        )
    }
    root = json.loads(ROOT_MANIFEST.read_text(encoding="utf-8"))
    flat = {
        f"plugins/{Path(p['source']).name}": p["source"].removeprefix("./") for p in root["plugins"]
    }
    compared = 0
    for path, record in wheel.items():
        head = "/".join(path.split("/")[:2])
        if head not in flat:
            continue  # the manifest, and the `plugins` folder entry above the plugins
        twin = checkout[flat[head] + path.removeprefix(head)]
        assert (twin.kind, twin.payload) == (record.kind, record.payload), path
        compared += 1
    assert compared > len(root["plugins"])
