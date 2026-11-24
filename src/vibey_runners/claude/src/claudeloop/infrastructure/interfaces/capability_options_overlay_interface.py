# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `infrastructure/agent/capability_overlay.py`: laying a run's capability
snapshot over the SDK options of one connect (SP-LOOPS Phase 4, Task 4; R5, R6, R12)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from claudeloop.domain.interfaces import AppliedCapabilitiesInterface


@runtime_checkable
class CapabilityOptionsOverlayInterface(Protocol):
    def apply(
        self, kwargs: dict[str, Any], applied: AppliedCapabilitiesInterface
    ) -> dict[str, Any]:
        """New `ClaudeAgentOptions` keyword arguments: `kwargs` with the snapshot's plugins,
        skills, MCP servers and folders first and the session's own after them, no user,
        project or local settings, strict MCP configuration, the snapshot's disallowed tools,
        and every disallowed tool taken out of `allowed_tools`. Never removes a snapshot entry
        and never changes `kwargs`. Raises `CapabilityFlagConflict` for an MCP server name both
        give."""
        ...
