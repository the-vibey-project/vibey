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
    """What every loop may be given: marketplaces, plugins, MCP servers and skills by name, the
    names the person or a project has switched off, and the person's own settings for the
    engine's web tools, instruction files and snapshot sweep."""

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

    @property
    def builtin_web(self) -> bool:
        """Whether a loop keeps its engine's own web tools (R4); off unless the person says."""
        ...

    @property
    def instruction_files(self) -> tuple[str, ...]:
        """Plain file names a loop reads from its run's folder into its system prompt (R8)."""
        ...

    @property
    def instruction_max_bytes(self) -> int:
        """The largest instruction file inlined; a larger one is named, never truncated."""
        ...

    @property
    def snapshot_max_age_days(self) -> int:
        """How old a run's snapshot folder may be before a worker's sweep removes it (R10)."""
        ...

    @classmethod
    def disable_names(cls, raw: object) -> tuple[str, ...]:
        """A `disable` list, from the person's file or a project's, held to the same rule: at
        most 256 plain names, each once. Raises `BundleError` at `loops.disable`."""
        ...

    @classmethod
    def option_safe_text(cls, value: object, path: str) -> str:
        """A source or ref anywhere (the bundle, the lock): non-empty, bounded, free of control
        characters and never starting with `-`. Raises `BundleError` at `path`."""
        ...

    def narrowed_by(self, disabled: Iterable[str]) -> Self:
        """This bundle without the plugins, MCP servers and skills named in `disabled`, with
        those names added to `disabled` (so a skill inside a kept plugin is dropped later too).
        Marketplaces are never removed: narrowing takes capabilities away, it adds none."""
        ...
