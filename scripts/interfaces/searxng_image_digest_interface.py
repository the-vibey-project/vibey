# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract `scripts/searxng_image_digest.py` implements. Interfaces declare; they never
consume."""

from __future__ import annotations

from typing import Protocol


class RegistryDigestInterface(Protocol):
    """Reads one image tag's digest from a public registry's read-only API."""

    def digest(self, repository: str, tag: str) -> str:
        """`sha256:<64 hex>` of `repository:tag`'s manifest (its multi-platform index when
        it has one), asked anonymously; raises `RuntimeError` naming what failed."""
        ...
