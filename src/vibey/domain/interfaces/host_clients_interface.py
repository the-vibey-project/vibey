# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for planning and rendering host-LLM MCP client configurations (ADR-0100).

The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.host_clients import (
        ClientProtocol,
        ConnectPlanItem,
        HostClientSpec,
        McpLaunchCommand,
    )


@runtime_checkable
class HostClientsInterface(Protocol):
    def all(self) -> tuple[HostClientSpec, ...]:
        """Every supported frontier LLM host client."""
        ...

    def by_id(self, client_id: str) -> HostClientSpec | None:
        """Look up a client specification by its identifier, or None."""
        ...

    def resolve_launch(
        self,
        *,
        which_vibey: str | None,
        python_executable: str,
        protocol: ClientProtocol = "mcp",
    ) -> McpLaunchCommand:
        """Resolve the command and args a client should launch: `vibey mcp` (an MCP server) or
        `vibey acp` (an ACP agent), or the Python fallback running the same."""
        ...

    def carries(
        self, spec: HostClientSpec, launch: McpLaunchCommand, existing_content: str | None
    ) -> bool:
        """Whether a config's text already holds exactly the entry `plan_one` would merge,
        however it is laid out; a JSON file with comments or trailing commas is read leniently.
        Only reads."""
        ...

    def snippet(self, spec: HostClientSpec, launch: McpLaunchCommand) -> str:
        """The `"<root key>": {"vibey": {...}}` text to paste into a JSON client's top-level
        object by hand, exactly the entry `plan_one` would merge."""
        ...

    def plan_one(
        self,
        spec: HostClientSpec,
        *,
        home_dir: str,
        project_dir: str,
        platform: str,
        launch: McpLaunchCommand,
        existing_content: str | None,
    ) -> ConnectPlanItem:
        """Compute the idempotent merge plan for one host client."""
        ...

    def resolve_clients(self, requested: Sequence[str] | None) -> tuple[HostClientSpec, ...]:
        """Resolve a list of client ids (or None/empty for all) into specifications."""
        ...
