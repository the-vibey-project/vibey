# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ULTRA's colour in the VS Code extension is the design tokens' `color.state.ultra`
(ADR-0063, ADR-0066): the manifest's contributed colour and the core's constant."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _ultra(mode: str) -> str:
    """`themes.<mode>.state.ultra` from the generated TypeScript tokens (resolved values)."""
    text = (ROOT / "design/dist/ts/tokens.ts").read_text("utf-8")
    themes = text[text.index("export const themes") :]
    dark, light = themes.split('"light": {', 1)
    section = dark if mode == "dark" else light
    state = section[section.index('"state": {') :]
    found = re.search(r'"ultra":\s*"(#[0-9a-fA-F]{6})"', state)
    assert found, f"no state.ultra in the {mode} theme"
    return found.group(1).lower()


def test_the_extension_contributes_ultra_in_the_tokens_colours() -> None:
    manifest = json.loads((ROOT / "clients/vscode/package.json").read_text("utf-8"))
    [colour] = [c for c in manifest["contributes"]["colors"] if c["id"] == "vibey.ultraEffort"]
    assert colour["defaults"]["dark"].lower() == _ultra("dark")
    assert colour["defaults"]["light"].lower() == _ultra("light")


def test_the_core_constant_is_the_tokens_colour() -> None:
    source = (ROOT / "packages/vibey-core/src/catalogue.ts").read_text("utf-8")
    assert f"dark: '{_ultra('dark')}'" in source
    assert f"light: '{_ultra('light')}'" in source
