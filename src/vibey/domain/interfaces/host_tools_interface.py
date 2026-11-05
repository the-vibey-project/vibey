# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the host-LLM tool catalogue and its call builder (ADR-0100).

The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from vibey.domain.hub_scope import HubScope

if TYPE_CHECKING:
    from vibey.domain.host_tools import HostTool, HubCall


@runtime_checkable
class HostToolsInterface(Protocol):
    def all(self) -> tuple[HostTool, ...]:
        """Every tool in the host catalogue."""
        ...

    def for_scopes(self, scopes: frozenset[HubScope]) -> tuple[HostTool, ...]:
        """The tools whose required scope is inside ``scopes``."""
        ...

    def by_name(self, name: str) -> HostTool | None:
        """The tool named ``name``, or None."""
        ...

    def mcp_definitions(self, scopes: frozenset[HubScope]) -> list[dict[str, Any]]:
        """The MCP ``tools/list`` definitions for the tools permitted by ``scopes``."""
        ...

    def build_call(
        self,
        name: str,
        arguments: Mapping[str, Any] | None,
        *,
        request_id: str,
    ) -> HubCall:
        """Validate ``arguments`` against the named tool and return the hub HTTP call."""
        ...

    def truncate(self, text: str, *, limit: int = 60_000) -> str:
        """Cap a tool response at ``limit`` chars with an explicit truncation notice (ADR-0075)."""
        ...

    def format_query(self, query: Sequence[tuple[str, str]]) -> str:
        """Render validated query pairs into a URL query string."""
        ...
