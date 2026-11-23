# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The manifest the wheel ships lists exactly the root marketplace's plugins (SP-LOOPS Phase 3c,
Task 0; operator ruling OR-4).

`src/vibey_tools/skills/packaged/marketplace.json` is rendered by `vibey-gh marketplace` from the
same members as the root manifest, with every source flattened to `./plugins/<folder>` because
the wheel lays both members' plugin trees side by side. These checks run on the checkout, with no
build: the slow wheel test (test_wheel_ships_default_marketplace.py) checks the built artifact.

Module-level test functions rather than a class with an interface beside it (ADR-0016), following
tests/meta/test_shipped_trees_are_reachable.py: the rule is about production code.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

REPO = Path(__file__).resolve().parents[2]
ROOT_MANIFEST = REPO / ".claude-plugin" / "marketplace.json"
PACKAGED = REPO / "src" / "vibey_tools" / "skills" / "packaged" / "marketplace.json"


def _load(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def test_the_packaged_manifest_lists_exactly_the_root_plugins() -> None:
    root, packaged = _load(ROOT_MANIFEST), _load(PACKAGED)
    assert {p["name"] for p in packaged["plugins"]} == {p["name"] for p in root["plugins"]}
    # The count is the root's, whatever it is; it is not pinned here.
    assert len(packaged["plugins"]) == len(root["plugins"])
    assert packaged["name"] == root["name"]


def test_every_packaged_source_is_the_flat_folder_of_its_root_source() -> None:
    root = {p["name"]: p["source"] for p in _load(ROOT_MANIFEST)["plugins"]}
    for plugin in _load(PACKAGED)["plugins"]:
        assert plugin["source"] == f"./plugins/{PurePosixPath(root[plugin['name']]).name}"


def test_every_packaged_plugin_has_a_plugin_json_at_its_root_source() -> None:
    root = {p["name"]: p["source"] for p in _load(ROOT_MANIFEST)["plugins"]}
    for plugin in _load(PACKAGED)["plugins"]:
        source = root[plugin["name"]]
        assert (REPO / source / ".claude-plugin" / "plugin.json").is_file(), source


def test_the_wheel_maps_every_root_plugin_tree_and_the_packaged_manifest() -> None:
    """Every member folder that holds a root plugin is force-included into the wheel's
    `plugins/`, so no plugin the manifest lists is missing from the install."""
    import tomllib

    include = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"][
        "build"
    ]["targets"]["wheel"]["force-include"]
    shipped = {source for source, target in include.items()}
    target = "vibey_skills/marketplace/plugins"
    folders = {
        PurePosixPath(p["source"]).parent.as_posix().removeprefix("./")
        for p in _load(ROOT_MANIFEST)["plugins"]
    }
    for folder in folders:
        assert include.get(folder) == target, folder
    packaged = PACKAGED.relative_to(REPO).as_posix()
    assert packaged in shipped
    assert include[packaged] == "vibey_skills/marketplace/.claude-plugin/marketplace.json"


def test_the_packaged_manifest_is_exactly_the_fresh_rendering() -> None:
    """Review I5: every field, not only names and sources. A plugin's version, description or
    category changed in a member and not re-rendered fails here (and CI's Gate 0 runs
    `vibey-gh marketplace --check` over both files)."""
    from vibey_gh.config import load_config
    from vibey_gh.marketplace import MarketplaceRenderer

    renderer = MarketplaceRenderer()
    cfg = load_config(REPO)
    assert _load(PACKAGED) == renderer.build_packaged(cfg)
    assert _load(ROOT_MANIFEST) == renderer.build(cfg)
    ok, message = renderer.check(cfg)
    assert ok, message


def test_ci_runs_the_marketplace_drift_check() -> None:
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "run: uv run vibey-gh marketplace --check" in ci


def test_a_changed_field_is_drift(tmp_path: Path) -> None:
    """The check the gate runs compares whole files: one field changed is caught."""
    from vibey_gh.config import GhConfig, MarketplaceConfig
    from vibey_gh.marketplace import MarketplaceRenderer

    member = tmp_path / "m"
    (member / ".claude-plugin").mkdir(parents=True)
    (member / "plugins" / "p" / ".claude-plugin").mkdir(parents=True)
    (member / "plugins" / "p" / ".claude-plugin" / "plugin.json").write_text("{}")
    manifest = {
        "name": "m",
        "owner": {"name": "o"},
        "plugins": [{"name": "p", "source": "./plugins/p", "version": "1.0.0"}],
    }
    (member / ".claude-plugin" / "marketplace.json").write_text(json.dumps(manifest))
    cfg = GhConfig(
        root=tmp_path,
        marketplace=MarketplaceConfig(name="x", members=("m",), packaged="packaged.json"),
    )
    renderer = MarketplaceRenderer()
    renderer.write(cfg)
    assert renderer.check(cfg)[0]
    manifest["plugins"][0]["version"] = "1.0.1"
    (member / ".claude-plugin" / "marketplace.json").write_text(json.dumps(manifest))
    ok, message = renderer.check(cfg)
    assert not ok and "out of date" in message
