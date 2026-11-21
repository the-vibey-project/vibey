# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_gate_prompter.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import AcpSessionContext


@runtime_checkable
class AcpGatePrompterInterface(Protocol):
    async def offer(
        self, session: AcpSessionContext, gates: Sequence[Mapping[str, Any]], *, turn_id: str
    ) -> None:
        """Put the open gates the session has not seen yet to the client, oldest first and at
        most `[acp] max_gate_prompts_per_turn` of them: each answerable one as a permission
        request, every other one (spend, deployment opt-in, value, unknown kind) as a message
        saying where to answer it.

        Runs inside a prompt turn that has begun on `session.state`. When the task running
        this is cancelled, the gate being asked is closed truthfully and the cancel propagates.
        """
        ...
