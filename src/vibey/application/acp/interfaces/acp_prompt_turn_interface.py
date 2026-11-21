# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_prompt_turn.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import AcpSessionContext
    from vibey.domain.acp.protocol import StopReason


@runtime_checkable
class AcpPromptTurnInterface(Protocol):
    async def run(
        self, session: AcpSessionContext, prompt: Sequence[Mapping[str, Any]], *, turn_id: str
    ) -> StopReason:
        """Run one prompt turn, streaming its updates, and propose its stop reason.

        The caller has already begun the turn on `session.state` and finishes it. When the
        task running this is cancelled, the turn reports what it can (the hub's real outcome
        if it answers within `[acp] cancel_grace_seconds`) and then lets the cancel propagate.
        """
        ...
