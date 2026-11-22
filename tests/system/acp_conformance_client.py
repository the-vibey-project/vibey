# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The editor side of the ACP conformance test: an `acp.Client` for the official SDK (SP-ACP).

The SDK's `ClientSideConnection` validates every message `vibey acp` sends against the
protocol's schema before it reaches this class, so what is recorded here is what an editor
built on the SDK would see. Updates are kept dumped back by alias (the protocol's camelCase), and
permission requests are answered by a policy the test sets: pick an option at once, or hold the
request until the test releases it (to answer late, after a cancel or a mode switch).

Every wait is event-driven and bounded: `wait_for` re-reads its condition after each message.
Declared by `interfaces/acp_conformance_client_interface.py`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any, Final

from acp import RequestError
from acp.schema import (
    AllowedOutcome,
    DeniedOutcome,
    RequestPermissionResponse,
)
from pydantic import BaseModel

NOT_DISPLAYED: Final = frozenset({"rawInput", "rawOutput", "_meta"})
"""Members an editor keeps as data and does not render."""


class AcpConformanceClient:
    """Declared by `interfaces/acp_conformance_client_interface.py`."""

    def __init__(self) -> None:
        self._updates: list[tuple[str, dict[str, Any]]] = []
        self._requests: list[dict[str, Any]] = []
        self._unexpected: list[str] = []
        self._changed = asyncio.Condition()
        self._pick: Callable[[Mapping[str, Any]], str | None] | None = None
        self._holding = False
        self._released = asyncio.Event()
        self._release_option = ""

    # -- what the SDK calls ---------------------------------------------------------------

    async def session_update(self, session_id: str, update: BaseModel, **kwargs: Any) -> None:
        dumped = update.model_dump(mode="json", by_alias=True, exclude_none=True)
        async with self._changed:
            self._updates.append((session_id, dumped))
            self._changed.notify_all()

    async def request_permission(
        self, session_id: str, tool_call: BaseModel, options: list[BaseModel], **kwargs: Any
    ) -> RequestPermissionResponse:
        request = {
            "session_id": session_id,
            "tool_call": tool_call.model_dump(mode="json", by_alias=True, exclude_none=True),
            "options": [
                option.model_dump(mode="json", by_alias=True, exclude_none=True)
                for option in options
            ],
        }
        async with self._changed:
            self._requests.append(request)
            self._changed.notify_all()
        return await self.permission_answer(request)

    async def read_text_file(self, **kwargs: Any) -> Any:
        return await self._refuse("fs/read_text_file")

    async def write_text_file(self, **kwargs: Any) -> Any:
        return await self._refuse("fs/write_text_file")

    async def create_terminal(self, **kwargs: Any) -> Any:
        return await self._refuse("terminal/create")

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._refuse(method)

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        async with self._changed:
            self._unexpected.append(method)
            self._changed.notify_all()

    # -- what the test reads --------------------------------------------------------------

    def updates(self, session_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(update for sid, update in self._updates if sid == session_id)

    def kinds(self, session_id: str) -> set[str]:
        return {update["sessionUpdate"] for update in self.updates(session_id)}

    def texts(self, session_id: str, kind: str = "agent_message_chunk") -> list[str]:
        return [
            update["content"]["text"]
            for update in self.updates(session_id)
            if update["sessionUpdate"] == kind and update["content"].get("type") == "text"
        ]

    def displayed(self) -> list[str]:
        shown: list[str] = []
        for _, update in self._updates:
            self._strings(update, shown)
        for request in self._requests:
            self._strings(request["options"], shown)
            self._strings(request["tool_call"], shown)
        return shown

    @property
    def permission_requests(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._requests)

    @property
    def unexpected(self) -> tuple[str, ...]:
        return tuple(self._unexpected)

    # -- the permission policy ------------------------------------------------------------

    def choose(self, pick: Callable[[Mapping[str, Any]], str | None]) -> None:
        self._holding = False
        self._pick = pick

    def hold(self) -> None:
        self._holding = True
        self._released = asyncio.Event()

    def release(self, option_id: str) -> None:
        self._release_option = option_id
        self._holding = False
        self._released.set()

    async def permission_answer(self, request: Mapping[str, Any]) -> RequestPermissionResponse:
        if self._holding:
            released = self._released
            await released.wait()
            chosen: str | None = self._release_option
        else:
            chosen = self._pick(request) if self._pick is not None else None
        if chosen is None:
            return RequestPermissionResponse(outcome=DeniedOutcome(outcome="cancelled"))
        return RequestPermissionResponse(
            outcome=AllowedOutcome(option_id=chosen, outcome="selected")
        )

    async def wait_for(self, check: Callable[[], bool], timeout: float) -> bool:
        async with self._changed:
            try:
                await asyncio.wait_for(self._changed.wait_for(check), timeout)
            except TimeoutError:
                return check()
        return True

    # -- helpers --------------------------------------------------------------------------

    async def _refuse(self, method: str) -> Any:
        async with self._changed:
            self._unexpected.append(method)
            self._changed.notify_all()
        raise RequestError.method_not_found(method)

    @classmethod
    def _strings(cls, value: Any, out: list[str]) -> None:
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, Mapping):
            for key, member in value.items():
                if key not in NOT_DISPLAYED:
                    cls._strings(member, out)
        elif isinstance(value, list):
            for member in value:
                cls._strings(member, out)
