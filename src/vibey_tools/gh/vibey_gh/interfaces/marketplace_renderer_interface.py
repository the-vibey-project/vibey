# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for rendering the root Claude Code marketplace (vibey ADR-0016)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from vibey_gh.config import GhConfig


class MarketplaceRendererInterface(Protocol):
    """Renders `<root>/.claude-plugin/marketplace.json` from the workspace members.

    Every method except `check` raises `vibey_gh.marketplace.MarketplaceError` (a
    `ValueError`) on a member the root cannot be rendered from; `check` reports that as
    a failed check instead.
    """

    def build(self, cfg: GhConfig) -> dict[str, Any]:
        """The manifest as data: name, owner, metadata, and every member's plugins."""
        ...

    def build_packaged(self, cfg: GhConfig) -> dict[str, Any]:
        """`build` with every `./` source flattened to `./plugins/<its last segment>`.

        The shape a package that ships every plugin tree side by side needs. Two plugins
        whose folders share a last segment raise `MarketplaceError`.
        """
        ...

    def render(self, cfg: GhConfig) -> str:
        """The exact text `write` puts on disk — deterministic for the same members."""
        ...

    def write(self, cfg: GhConfig) -> Path:
        """Write the manifest to its fixed path under the root and return that path.

        With `[marketplace] packaged` set, the packaged rendering is written as well.
        """
        ...

    def check(self, cfg: GhConfig) -> tuple[bool, str]:
        """Whether the file(s) on disk are what the members render to, and why not."""
        ...
