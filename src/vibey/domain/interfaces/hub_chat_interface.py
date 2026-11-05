# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the hub's chat command parser and turn renderer (ADR-0100).

Mirrors `vibey/domain/hub_chat.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.domain.hub_chat import ChatIntent, ChatSlashSpec


@runtime_checkable
class HubChatInterface(Protocol):
    def slash_commands(self) -> tuple[ChatSlashSpec, ...]:
        """Every `/` command the hub chatcomposer offers."""
        ...

    def help_text(self) -> str:
        """A human-readable summary of the `/` commands and natural-language shortcuts."""
        ...

    def parse(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        open_gates: Sequence[Mapping[str, Any]] = (),
    ) -> ChatIntent:
        """Parse a user chat message into a validated `ChatIntent`."""
        ...

    def parse_gate_answer(self, kind: str, raw: str) -> dict[str, Any]:
        """Parse a gate answer token or JSON object according to the gate's `kind`."""
        ...

    def format_gate_prompt(self, gate: Mapping[str, Any]) -> dict[str, Any]:
        """Annotate a gate document with `is_spend` and `requires_scope` for chat cards."""
        ...

    def summarize_turn(
        self,
        *,
        intent: ChatIntent,
        tool_calls: Sequence[Mapping[str, Any]],
        gates: Sequence[Mapping[str, Any]],
        project_id: UUID | None,
    ) -> dict[str, Any]:
        """Build the structured chat turn document returned by `POST /api/v1/chat/messages`."""
        ...
