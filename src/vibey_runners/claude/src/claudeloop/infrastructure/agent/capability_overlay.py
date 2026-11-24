# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lays a run's capability snapshot over the SDK options of one connect (SP-LOOPS Phase 4,
Task 4; R5, R6, R12).

Applied by `build_turn_options` on every connect, so a mid-run `claudeloop attach`, `skill` or
`connector`, which replaces the session's own resources wholesale, can never drop what the
snapshot gave (Review Focus 1). The snapshot comes first and the session's own resources follow
it; nothing the snapshot gave is ever removed.

- `setting_sources = []`: no user, project or local Claude settings. Without it the SDK reads
  user and project settings as soon as `skills` is set (R5).
- `strict_mcp_config = True`: only the MCP servers named here.
- `skills`: the catalog's qualified names, then the session's own; an empty list is skills off.
  A session's `"all"` is not a name and does not widen the catalog (R6).
- An MCP server name both give is refused, never overridden (R12).
- Every disallowed tool is taken out of `allowed_tools`, so a tool is never both (R4).

Declared by `interfaces/capability_options_overlay_interface.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claudeloop.domain.errors import CapabilityFlagConflict
from claudeloop.domain.interfaces import AppliedCapabilitiesInterface


class CapabilityOptionsOverlay:
    """Declared by `interfaces/capability_options_overlay_interface.py`."""

    def apply(
        self, kwargs: dict[str, Any], applied: AppliedCapabilitiesInterface
    ) -> dict[str, Any]:
        merged = dict(kwargs)
        merged["setting_sources"] = []
        merged["strict_mcp_config"] = True
        merged["plugins"] = self._plugins(applied, kwargs.get("plugins") or [])
        merged["skills"] = self._skills(applied, kwargs.get("skills"))
        merged["mcp_servers"] = self._servers(applied, kwargs.get("mcp_servers") or {})
        merged["add_dirs"] = self._unique(
            [Path(folder) for folder in applied.add_dirs]
            + [Path(folder) for folder in kwargs.get("add_dirs") or []]
        )
        disallowed = list(applied.disallowed_tools)
        merged["disallowed_tools"] = disallowed
        merged["allowed_tools"] = [
            tool
            for tool in kwargs.get("allowed_tools") or []
            if tool.partition("(")[0] not in disallowed
        ]
        return merged

    def _plugins(
        self, applied: AppliedCapabilitiesInterface, own: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        snapshot = [{"type": "local", "path": folder} for folder in applied.plugin_dirs]
        return self._unique(snapshot + list(own))

    def _skills(self, applied: AppliedCapabilitiesInterface, own: object) -> list[str]:
        names = list(own) if isinstance(own, list) else []
        return self._unique(list(applied.skills) + names)

    @staticmethod
    def _servers(applied: AppliedCapabilitiesInterface, own: dict[str, Any]) -> dict[str, Any]:
        servers: dict[str, Any] = {name: dict(cfg) for name, cfg in applied.mcp_servers.items()}
        for name, cfg in own.items():
            if name in servers:
                raise CapabilityFlagConflict(
                    f"MCP server {name!r} is given by this run's capability snapshot and by "
                    "the session's own connectors; rename the connector or leave it out"
                )
            servers[name] = cfg
        return servers

    @staticmethod
    def _unique[T](items: list[T]) -> list[T]:
        """`items` without repeats, first occurrence kept: a union in order."""
        kept: list[T] = []
        for item in items:
            if item not in kept:
                kept.append(item)
        return kept
