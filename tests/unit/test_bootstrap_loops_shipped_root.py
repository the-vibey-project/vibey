# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which folder the shipped marketplace is locked from (SP-LOOPS Phase 3c, Task 0).

Installed, it is the wheel's `vibey_skills/marketplace/`. From a checkout `marketplace_root()`
falls back to the skills tenant, whose manifest lists only its own plugins, so the checkout locks
the repository root's manifest, which lists every member's.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.defaults import DEFAULT_MARKETPLACE_NAME
from vibey_runners.common.capabilities.resolver import CapabilityResolver

from vibey import bootstrap

REPO = Path(__file__).resolve().parents[2]
MANIFEST = Path(".claude-plugin") / "marketplace.json"


def _plugins(root: Path) -> list[str]:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    return [plugin["name"] for plugin in manifest["plugins"]]


def test_a_checkout_locks_the_root_marketplace_with_every_plugin(tmp_path: Path) -> None:
    root = bootstrap.loops_shipped_root()
    assert root == REPO
    assert len(_plugins(root)) == len(_plugins(REPO))
    store = bootstrap.loops_marketplace_store(tmp_path / "config" / "vibey.toml")
    assert store.shipped_root() == REPO
    resolver = CapabilityResolver(
        tmp_path / "loops.lock", tmp_path / "snapshots", shipped_source="t"
    )
    snapshot = resolver.resolve(BundleSpec.default(), (), {DEFAULT_MARKETPLACE_NAME: root})
    assert snapshot.skills.skills  # the default research plugins resolve from the root manifest


def test_an_installed_marketplace_root_is_used_as_it_is(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = tmp_path / "site-packages" / "vibey_skills" / "marketplace"
    monkeypatch.setattr(bootstrap, "marketplace_root", lambda: installed)
    assert bootstrap.loops_shipped_root() == installed


def test_a_checkout_without_a_root_manifest_keeps_the_tenant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A source tree that carries no root manifest (an sdist unpacked) keeps the tenant's."""
    tenant = REPO / "src" / "vibey_tools" / "skills"
    monkeypatch.setattr(bootstrap, "marketplace_root", lambda: tenant)
    monkeypatch.setattr(bootstrap, "LOOPS_MANIFEST", Path("no-such") / "marketplace.json")
    assert bootstrap.loops_shipped_root() == tenant
