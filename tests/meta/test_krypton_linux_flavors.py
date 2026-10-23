# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""krypton desktop has three Linux flavors -- Arch, Ubuntu and Fedora (#1188): CI builds
each, and each has a declared native package recipe or a planned one in PACKAGING.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
DESKTOP = ROOT / "clients" / "desktop"
FLAVORS = ("arch", "ubuntu", "fedora")


def _desktop_cells() -> dict[str, dict[str, Any]]:
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    include: list[dict[str, Any]] = workflow["jobs"]["desktop"]["strategy"]["matrix"]["include"]
    return {cell["distro"]: cell for cell in include}


def test_ci_builds_krypton_desktop_on_every_linux_flavor() -> None:
    cells = _desktop_cells()
    assert set(FLAVORS) <= set(cells)
    assert cells["fedora"]["container"] == "fedora:latest"


def test_every_linux_flavor_has_its_own_toolchain_step() -> None:
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    conditions = {step.get("if") for step in workflow["jobs"]["desktop"]["steps"]}
    for flavor in FLAVORS:
        assert f"matrix.distro == '{flavor}'" in conditions


def test_fedora_has_a_declared_rpm_spec_named_in_packaging() -> None:
    spec = DESKTOP / "packaging" / "fedora" / "krypton-desktop.spec"
    text = spec.read_text(encoding="utf-8")
    assert "Name:           krypton-desktop" in text
    assert "%meson_install" in text
    assert "packaging/fedora/krypton-desktop.spec" in (DESKTOP / "PACKAGING.md").read_text(
        encoding="utf-8"
    )
