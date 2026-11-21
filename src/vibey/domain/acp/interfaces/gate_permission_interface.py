# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/gate_permission.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.gate_permission import PermissionChoice


@runtime_checkable
class GatePermissionMapperInterface(Protocol):
    """Turns an open gate into `session/request_permission` options, or says why it cannot."""

    def gate_id(self, gate: Mapping[str, Any]) -> str | None:
        """The gate's id in canonical UUID form, or None when it is not a UUID."""
        ...

    def options_for(self, gate: Mapping[str, Any]) -> tuple[PermissionChoice, ...]:
        """The options an editor may offer for `gate`, in order, ending with the agent's own
        "Leave it open". Empty for a spend gate (by kind or by flag), the deployment opt-in, a
        gate whose answer is a value, an unknown kind, a gate whose id is not a UUID and a
        gate with no usable option."""
        ...

    def refusal_text(self, gate: Mapping[str, Any]) -> str:
        """What to tell the operator about a gate `options_for` does not offer."""
        ...
