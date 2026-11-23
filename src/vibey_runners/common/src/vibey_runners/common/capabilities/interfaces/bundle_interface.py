# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of the loop capability bundle (SP-LOOPS Task 3)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, Self, runtime_checkable

from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.plugin_spec import PluginSpec


@runtime_checkable
class BundleSpecInterface(Protocol):
    """What every loop may be given: marketplaces, plugins, MCP servers and skills by name, and
    the names the person or a project has switched off."""

    @property
    def marketplaces(self) -> tuple[MarketplaceSpec, ...]: ...

    @property
    def plugins(self) -> tuple[PluginSpec, ...]: ...

    @property
    def mcp_servers(self) -> tuple[McpServerSpec, ...]: ...

    @property
    def skills(self) -> tuple[str, ...]: ...

    @property
    def disabled(self) -> frozenset[str]: ...

    def narrowed_by(self, disabled: Iterable[str]) -> Self:
        """This bundle without the plugins, MCP servers and skills named in `disabled`, with
        those names added to `disabled` (so a skill inside a kept plugin is dropped later too).
        Marketplaces are never removed: narrowing takes capabilities away, it adds none."""
        ...
