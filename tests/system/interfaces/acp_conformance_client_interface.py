# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `tests/system/acp_conformance_client.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from acp.schema import RequestPermissionResponse

type Update = Mapping[str, Any]
"""One `session/update`'s `update`, as the SDK parsed it, dumped back by alias."""


@runtime_checkable
class AcpConformanceClientInterface(Protocol):
    """The editor side of the conformance test: an `acp.Client` for the official SDK's
    `ClientSideConnection` that records every update and permission request it is sent and
    answers permission requests by a policy the test sets."""

    def updates(self, session_id: str) -> tuple[Update, ...]:
        """Every update for `session_id`, in the order the SDK delivered them."""
        ...

    def kinds(self, session_id: str) -> set[str]:
        """The `sessionUpdate` kinds `session_id` was sent."""
        ...

    def texts(self, session_id: str, kind: str = "agent_message_chunk") -> list[str]:
        """The text of every `kind` update (a message chunk) for `session_id`."""
        ...

    def displayed(self) -> list[str]:
        """Every string an editor would show from the updates received (titles, messages,
        tool content, plan entries, command descriptions, permission options): `rawInput`,
        `rawOutput` and `_meta` are data, not display, and are left out."""
        ...

    @property
    def permission_requests(self) -> tuple[Mapping[str, Any], ...]:
        """Every `session/request_permission`: `{"session_id", "tool_call", "options"}`."""
        ...

    @property
    def unexpected(self) -> tuple[str, ...]:
        """Any other client method the agent called (fs, terminal, extensions)."""
        ...

    def choose(self, pick: Callable[[Mapping[str, Any]], str | None]) -> None:
        """Answer each permission request at once with the option id `pick` returns (any id,
        offered or not), or with the `cancelled` outcome when it returns None."""
        ...

    def hold(self) -> None:
        """Hold each permission request unanswered until `release`."""
        ...

    def release(self, option_id: str) -> None:
        """Answer the held requests now, selecting `option_id`."""
        ...

    def poke(self) -> None:
        """Wake every `wait_for` to read its condition again; safe from any thread."""
        ...

    async def wait_for(self, check: Callable[[], bool], timeout: float) -> bool:
        """Whether `check()` held, re-read after every message, within `timeout` seconds."""
        ...

    async def permission_answer(self, request: Mapping[str, Any]) -> RequestPermissionResponse:
        """The answer the current policy gives `request` (held ones wait for `release`)."""
        ...
