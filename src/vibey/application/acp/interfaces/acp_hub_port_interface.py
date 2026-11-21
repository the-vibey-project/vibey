# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's port onto the hub, as the scoped agent principal (SP-ACP, ADR-0100).

Implemented by `infrastructure/acp/acp_hub_client.py` over the MCP `HubGateway`. Every failure
to reach the hub, or a refusal where a result is expected, surfaces as a `VibeyError` subclass.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.application.acp.dto import HubToolResult, HubTurn, LedgerPage
    from vibey.domain.hub_scope import HubScope


@runtime_checkable
class AcpHubPortInterface(Protocol):
    async def chat(self, message: str, *, project_id: UUID | None, request_id: str) -> HubTurn:
        """Run one chat turn on the hub; a refusal raises, naming the status the hub gave."""
        ...

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any], *, request_id: str
    ) -> HubToolResult:
        """Run one host tool; a refusal is a result with `ok` false, not an error."""
        ...

    async def ledger_after(self, project_id: UUID, after: int, limit: int) -> LedgerPage:
        """At most `limit` ledger events with a `seq` after `after`, oldest first."""
        ...

    async def healthy(self) -> bool:
        """Whether the hub answers its liveness route; never raises."""
        ...

    def agent_scopes(self) -> frozenset[HubScope]:
        """The scopes the hub grants the agent principal (`[hub] agent_scopes`)."""
        ...
