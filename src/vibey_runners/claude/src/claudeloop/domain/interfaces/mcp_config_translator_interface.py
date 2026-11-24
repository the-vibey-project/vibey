# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `domain/mcp_config.py`: one MCP server from a run's capability snapshot, as
the SDK config a session is given (SP-LOOPS Phase 4, Task 5; R7)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec


@runtime_checkable
class McpConfigTranslatorInterface(Protocol):
    def translate(self, server: McpServerSpec) -> dict[str, object]:
        """`server` with an explicit transport. `local` is `{"type": "stdio"}` started through
        the scrubbed launcher, with no `env` key ever; `remote` is `{"type": "http"}`, never
        `sse`. Pure: no environment, no clock. Raises `ValueError` for a spec that is neither."""
        ...
