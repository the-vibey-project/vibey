# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The client channel a prompt turn writes through, keeping what it showed (SP-ACP, Task 6).

A prompt turn and its gate prompter send their updates through this channel; each update the
client was sent is then kept in the session's log, as `AcpSessionReplayInterface.recordable`
says (messages, tool calls and their outcomes, plans). The live ledger feed writes to the
client directly, not through here: its summaries are re-readable from the ledger and are not
kept. Permission requests pass straight through and are never kept: a replay never asks.

Declared by `interfaces/client_channel_interface.py::ClientChannelInterface`.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from vibey.application.acp.interfaces.acp_session_journal_interface import (
    AcpSessionJournalInterface,
)
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.interfaces.session_replay_interface import AcpSessionReplayInterface


class AcpJournalingChannel:
    """Declared by `interfaces/client_channel_interface.py::ClientChannelInterface`."""

    def __init__(
        self,
        channel: ClientChannelInterface,
        journal: AcpSessionJournalInterface,
        replay: AcpSessionReplayInterface,
    ) -> None:
        self._channel = channel
        self._journal = journal
        self._replay = replay

    @property
    def client_capabilities(self) -> Mapping[str, Any]:
        return self._channel.client_capabilities

    @client_capabilities.setter
    def client_capabilities(self, value: Mapping[str, Any]) -> None:
        self._channel.client_capabilities = value

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        await self._channel.notify_update(session_id, update)
        # Kept once the client was sent it: the log holds what the session showed.
        kept = self._replay.recordable(update)
        if kept is not None:
            self._journal.record(session_id, *kept)

    async def request_permission(
        self,
        session_id: str,
        tool_call: Mapping[str, Any],
        options: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> str | None:
        return await self._channel.request_permission(
            session_id, tool_call, options, timeout=timeout
        )

    def cancel_permissions(self, session_id: str) -> tuple[str, ...]:
        return self._channel.cancel_permissions(session_id)
