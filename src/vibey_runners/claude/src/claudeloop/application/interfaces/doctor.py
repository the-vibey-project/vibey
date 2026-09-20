# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `doctor` needs from the outside world.

Kept separate from the larger AgentGateway/SessionCatalog seams so `doctor`
stays cheap to run and never requires a live SDK connection.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from claudeloop.application.dto import BackendStatus, ToolCallStatus


@runtime_checkable
class DoctorEnvironment(Protocol):
    def find_claude_cli(self) -> str | None: ...
    def find_bundled_claude_cli(self) -> str | None:
        """The Claude Code CLI shipped inside claude-agent-sdk, which the SDK itself
        launches when present — so a machine (or container) with no `claude` on
        PATH can still run."""
        ...

    def claude_cli_version(self, path: str) -> str | None: ...
    def is_authenticated(self) -> bool: ...
    def configured_mcp_servers(self) -> list[str]: ...
    def anthropic_sdk_version(self) -> str | None: ...
    def api_surface_method_count(self) -> int | None: ...
    def probe_backend(self, base_url: str, auth_token: str) -> BackendStatus:
        """Ask a profile's endpoint whether it answers, and which models it has."""
        ...

    def probe_tool_calling(self, base_url: str, auth_token: str, model: str) -> ToolCallStatus:
        """Ask ``model`` to call a trivial tool and report whether it really did."""
        ...
