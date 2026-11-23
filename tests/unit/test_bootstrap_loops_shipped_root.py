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


def test_a_tenant_without_its_manifest_still_finds_the_root_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review B1: in the editable image `marketplace_root()` can raise; the repository root's
    manifest is still the shipped marketplace."""

    def missing() -> Path:
        raise FileNotFoundError("no marketplace")

    monkeypatch.setattr(bootstrap, "marketplace_root", missing)
    assert bootstrap.loops_shipped_root() == REPO


def test_no_manifest_anywhere_is_a_named_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing() -> Path:
        raise FileNotFoundError("no marketplace")

    monkeypatch.setattr(bootstrap, "marketplace_root", missing)
    monkeypatch.setattr(bootstrap, "LOOPS_MANIFEST", Path("no-such") / "marketplace.json")
    with pytest.raises(FileNotFoundError, match="no shipped marketplace"):
        bootstrap.loops_shipped_root()


def test_the_image_copies_both_manifests_and_asserts_the_lookup() -> None:
    """Review B1's regression guard, on the files that build and check the image."""
    dockerfile = (REPO / "deploy" / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY .claude-plugin/marketplace.json ./.claude-plugin/" in dockerfile
    assert (
        "COPY src/vibey_tools/skills/.claude-plugin/marketplace.json "
        "./src/vibey_tools/skills/.claude-plugin/" in dockerfile
    )
    assert "COPY --from=build /app/.claude-plugin /app/.claude-plugin" in dockerfile
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "Image contract - the shipped marketplace is found and carries every root plugin" in ci
    assert "loops_shipped_root" in ci


def _image_probe() -> str:
    """The Python the image contract step runs inside the built image, read from ci.yml."""
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    step = ci.split("Image contract - the shipped marketplace is found", 1)[1]
    body = step.split("<<'PY'\n", 1)[1].split("\n          PY\n", 1)[0]
    return "\n".join(line.removeprefix("          ") for line in body.splitlines())


def test_the_image_probe_passes_on_this_checkout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exec(compile(_image_probe(), "<image-probe>", "exec"), {"__name__": "__main__"})  # noqa: S102
    assert capsys.readouterr().out.strip() == str(len(_plugins(REPO)))


def test_the_image_probe_fails_when_a_listed_plugin_folder_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fix review M1: an image whose manifest lists a plugin whose folder was not copied fails
    the contract step, naming the plugin, even though the count matches."""
    (tmp_path / ".claude-plugin").mkdir()
    manifest = {
        "name": "vibey",
        "plugins": [
            {"name": "present", "source": "./src/a/plugins/present"},
            {"name": "dropped", "source": "./src/b/plugins/dropped"},
        ],
    }
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(json.dumps(manifest))
    (tmp_path / "src/a/plugins/present/.claude-plugin").mkdir(parents=True)
    (tmp_path / "src/a/plugins/present/.claude-plugin/plugin.json").write_text("{}")
    monkeypatch.setattr(bootstrap, "loops_shipped_root", lambda: tmp_path)
    with pytest.raises(SystemExit) as exited:
        exec(compile(_image_probe(), "<image-probe>", "exec"), {"__name__": "__main__"})  # noqa: S102
    assert exited.value.code == 1
    assert "plugin folders missing from the image: dropped" in capsys.readouterr().err
