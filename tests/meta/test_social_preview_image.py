# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The docs site declares a favicon and a 1200x630 social-preview image.

The social-preview raster is the canonical design-system card (byte-identical to
design/dist/icons/web/social-preview.png), declared at docs/img/social-preview.png so the
og:image/twitter:image tags injected by scripts/inject_docs_meta.py resolve. The favicon is
a three-dot mark over a dark rounded square, tracing the same purple-to-blue span as the
README's paper and book badges.
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
FAVICON = REPO_ROOT / "docs" / "img" / "favicon.svg"
SOCIAL_PREVIEW = REPO_ROOT / "docs" / "img" / "social-preview.png"
PROPERDOCS = REPO_ROOT / "properdocs.yml"


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Read the PNG's own IHDR chunk, independent of any generator module."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    # IHDR is the first chunk: length(4) + "IHDR"(4) + width(4) + height(4)
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_png_dimensions_are_1200_by_630() -> None:
    assert _png_dimensions(SOCIAL_PREVIEW) == (1200, 630)


def test_favicon_svg_is_well_formed() -> None:
    ET.fromstring(FAVICON.read_text(encoding="utf-8"))


def test_properdocs_yml_theme_names_the_favicon() -> None:
    cfg = yaml.safe_load(PROPERDOCS.read_text(encoding="utf-8"))
    assert cfg["theme"]["name"] == "mkdocs"
    assert cfg["theme"]["favicon"] == "img/favicon.svg"
