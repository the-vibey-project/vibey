# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The design system's outputs are exactly what its tokens generate, and every colour pair it
promises is legible (WCAG 2.2 AA) in both themes."""

from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_design() -> tuple[type, type, type]:
    """Import scripts/design without leaving `scripts/` on sys.path.

    `scripts/interfaces` is a top-level package name other tests' tools also use, so the path
    and the modules it brought are removed again once the design classes are in hand.
    """
    before = set(sys.modules)
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from design.generate import DesignGenerator  # noqa: PLC0415

        from design.tokens import Colour, TokenSet  # noqa: PLC0415
    finally:
        while str(REPO / "scripts") in sys.path:  # generate.py inserts it a second time
            sys.path.remove(str(REPO / "scripts"))
        for name in set(sys.modules) - before:
            if name == "interfaces" or name.startswith(("interfaces.", "design")):
                del sys.modules[name]
    return DesignGenerator, Colour, TokenSet


DesignGenerator, Colour, TokenSet = _load_design()

GENERATOR = DesignGenerator(REPO)


def test_no_generated_file_has_drifted_from_the_tokens() -> None:
    """Every stylesheet copy, the TS/GTK/C/TeX outputs, the paper palette, the SVG masters and
    the PNG set match a fresh generation. Fix: `python3 scripts/design/generate.py [--rasters]`."""
    problems = GENERATOR.check()
    assert not problems, "\n".join(problems)


def test_the_check_is_reachable_from_the_command_line() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/design/generate.py", "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "result",
    GENERATOR.contrast().results(),
    ids=lambda r: f"{r.theme}:{r.foreground}/{r.background}",
)
def test_every_declared_colour_pair_meets_wcag_aa(result) -> None:  # type: ignore[no-untyped-def]
    assert result.passes, (
        f"{result.theme}: {result.foreground} {result.foreground_hex} on {result.background} "
        f"{result.background_hex} is {result.ratio:.2f}:1, below {result.minimum}:1 ({result.rule})"
    )


def test_the_contrast_arithmetic_matches_wcag() -> None:
    """Anchors from the WCAG definition, so a broken formula cannot pass its own audit."""
    assert Colour.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert Colour.contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)
    assert Colour.contrast("#ffffff", "#ffffff") == pytest.approx(1.0)


def test_both_themes_define_exactly_the_same_roles() -> None:
    tokens = TokenSet(REPO / "design/tokens")
    roles = {
        theme: {t.path.split(".", 2)[2] for t in tokens.group(f"theme.{theme}")}
        for theme in ("dark", "light")
    }
    assert roles["dark"] == roles["light"], roles["dark"] ^ roles["light"]
    for required in (
        "accent.default",
        "status.success",
        "status.warning",
        "status.danger",
        "status.info",
        "status.ultra",
        "bg.surface",
        "bg.raised",
        "bg.overlay",
    ):
        assert required in roles["dark"], required


def test_every_text_role_in_every_theme_is_audited() -> None:
    """A new text or status colour cannot slip in without a contrast rule naming it."""
    rules = json.loads((REPO / "design/contrast.json").read_text(encoding="utf-8"))["rules"]
    audited = {fg for rule in rules for fg in rule["foreground"]}
    tokens = TokenSet(REPO / "design/tokens")
    for token in tokens.group("theme.dark"):
        role = token.path.split(".", 2)[2]
        if role.split(".")[0] in ("text", "status", "state", "syntax", "lane"):
            assert role in audited, f"{role} has no contrast rule in design/contrast.json"


def test_ultra_is_distinct_from_every_other_status_colour() -> None:
    tokens = TokenSet(REPO / "design/tokens")
    for theme in ("dark", "light"):
        ultra = tokens.hex(f"theme.{theme}.status.ultra")
        for other in ("success", "warning", "danger", "info"):
            assert ultra != tokens.hex(f"theme.{theme}.status.{other}")
        assert ultra != tokens.hex(f"theme.{theme}.accent.default")


def test_the_paper_palette_is_the_one_the_paper_always_drew_with() -> None:
    """Rendering unchanged in meaning: the 17 print colours keep their names, order and values."""
    expected = [
        "17324D",
        "2F6B9A",
        "4FA3D1",
        "168A8A",
        "2EA97F",
        "3A8F5B",
        "C68A19",
        "E0A83A",
        "B24C4C",
        "D98A8A",
        "6B5BD2",
        "A89BE8",
        "64748B",
        "A7B2C2",
        "D6E0EA",
        "EEF5FA",
        "F6F9FC",
    ]
    names = [
        "ink",
        "blue",
        "sky",
        "teal",
        "mint",
        "green",
        "gold",
        "amber",
        "red",
        "rose",
        "violet",
        "lilac",
        "gray",
        "silver",
        "line",
        "wash",
        "mist",
    ]
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.find_spec("vibey_gh.paper")
    assert spec is not None, "vibey_gh must be importable (it is a workspace member)"
    from vibey_gh import paper  # noqa: PLC0415

    lines = [line for line in paper.PREAMBLE if line.startswith(r"\definecolor")]
    assert lines == [
        rf"\definecolor{{vibey{n}}}{{HTML}}{{{h}}}" for n, h in zip(names, expected, strict=True)
    ]


def test_every_docs_site_reads_one_stylesheet_and_offers_three_themes() -> None:
    config = json.loads((REPO / "design/design.json").read_text(encoding="utf-8"))
    copies = {(REPO / t).read_bytes() for t in config["stylesheet"]["targets"]}
    assert len(copies) == 1, "the documentation sites' stylesheets have drifted apart"
    css = copies.pop().decode()
    assert "GENERATED by scripts/design/generate.py" in css
    assert "@media (prefers-color-scheme: dark)" in css
    assert ':root[data-theme="dark"]' in css and ':root[data-theme="light"]' in css
    assert "prefers-reduced-motion" in css
    script = (REPO / config["script"]["targets"][0]).read_text(encoding="utf-8")
    assert 'THEME_MODES = ["light", "dark", "system"]' in script
    assert "localStorage" in script and 'addEventListener("change"' in script


def test_every_platform_output_carries_the_three_theme_modes() -> None:
    ts = (REPO / "design/dist/ts/tokens.ts").read_text(encoding="utf-8")
    assert 'export type ThemeMode = "light" | "dark" | "system";' in ts
    assert 'DEFAULT_THEME_MODE: ThemeMode = "system"' in ts
    header = (REPO / "design/dist/c/vibey_tokens.h").read_text(encoding="utf-8")
    assert "VIBEY_THEME_MODE_DEFAULT VIBEY_THEME_MODE_SYSTEM" in header
    assert "ADW_COLOR_SCHEME_DEFAULT" in header
    for name in ("vibey.css", "vibey-dark.css"):
        gtk = (REPO / "design/dist/gtk" / name).read_text(encoding="utf-8")
        assert "@define-color accent_bg_color" in gtk


def test_every_generated_text_file_says_it_is_generated() -> None:
    for rel in GENERATOR.outputs():
        if rel.suffix in (".css", ".ts", ".h", ".tex", ".js", ".py"):
            head = (REPO / rel).read_text(encoding="utf-8")[:600]
            assert "GENERATED by scripts/design/generate.py" in head, rel


def test_icon_sizes_are_what_their_names_say() -> None:
    """Read each PNG's own IHDR, independent of the generator that wrote it."""
    manifest = json.loads((REPO / "design/dist/icons/manifest.json").read_text(encoding="utf-8"))[
        "rasters"
    ]
    assert len(manifest) >= 29
    for rel, entry in manifest.items():
        data = (REPO / rel).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", rel
        width, height = struct.unpack(">II", data[16:24])
        assert (width, height) == (entry["width"], entry["height"]), rel
        size = re.search(r"(\d+)x(\d+)(@2x)?", rel)
        if size and "hicolor" in rel:
            assert width == int(size.group(1)), rel
    ios = (REPO / "design/dist/icons/ios/AppIcon-1024.png").read_bytes()
    assert ios[25] == 2, "the iOS marketing icon must be opaque (RGB, no alpha)"
