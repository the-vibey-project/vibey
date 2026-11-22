# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/modes.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.modes import AcpMode
    from vibey.domain.hub_scope import HubScope


@runtime_checkable
class AcpModesInterface(Protocol):
    """The session modes `[acp] modes` offers, and what each may do."""

    def available(self) -> tuple[AcpMode, ...]:
        """The offered modes, in the order `[acp] modes` lists them."""
        ...

    def scopes_for(self, mode_id: str, agent_scopes: frozenset[HubScope]) -> frozenset[HubScope]:
        """The mode's scopes intersected with the hub's grant; `UnknownMode` for an id not offered."""
        ...

    def admits(
        self,
        mode_id: str,
        *,
        scope: HubScope,
        session_scope: HubScope,
        agent_scopes: frozenset[HubScope],
    ) -> bool:
        """Whether a session in `mode_id` may run a tool the hub authorises as `scope` and the
        mode reads as `session_scope`: the mode must hold the second, the hub's grant the first."""
        ...

    def session_modes(self, current: str) -> dict[str, Any]:
        """ACP's `SessionModeState` as a JSON-ready dict."""
        ...
