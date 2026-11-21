# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub keeps each ACP session's log, for the principal that created it (SP-ACP, Task 6).

`vibey acp` runs where no database credential is (ADR-0055, ADR-0100), so it keeps its sessions
through the hub, as the scoped agent principal. Every call is authorised with
`HubAction.RECORD_ACP_SESSION` before anything is read, and a session is only ever read or
written by the principal that created it. A session id that does not exist, belongs to another
principal, or -- for a read that names a folder -- was kept under another folder is refused
with the same `HubForbidden` and the same words, so a guessed id learns nothing.

The list is a keyset over `(updated_at, session_id)`, newest first; its cursor is opaque to the
client: the URL-safe base64 of `<updated_at ISO 8601>|<session_id>`.

Declared by `interfaces/acp_session_service_interface.py`.
"""

import base64
import binascii
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from vibey.application.acp.dto import SessionEvent, SessionRecord
from vibey.application.acp.interfaces.acp_session_repository_interface import (
    AcpSessionRepositoryInterface,
)
from vibey.application.dto import HubPrincipal
from vibey.domain.acp.session_log import (
    SESSION_ID_SHAPE,
    InvalidSessionCursor,
    SessionEventConflict,
)
from vibey.domain.hub_scope import HubAction, HubForbidden
from vibey.domain.interfaces.hub_scope_interface import HubScopePolicyInterface

_SEPARATOR = "|"


class AcpSessionService:
    """Declared by `interfaces/acp_session_service_interface.py::AcpSessionServiceInterface`."""

    def __init__(
        self, repository: AcpSessionRepositoryInterface, policy: HubScopePolicyInterface
    ) -> None:
        self._repository = repository
        self._policy = policy

    async def create(self, principal: HubPrincipal, session_id: str, cwd: str) -> None:
        self._authorise(principal)
        kept = await self._repository.owner(session_id)
        if kept is not None:
            owner, folder = kept
            if owner != principal.name:
                raise self._unknown(session_id)
            if folder != cwd:
                raise SessionEventConflict(
                    f"session {session_id} is already kept under another folder"
                )
            return
        await self._repository.create(session_id, cwd, principal.name)

    async def append(
        self,
        principal: HubPrincipal,
        session_id: str,
        seq: int,
        kind: str,
        payload: Mapping[str, Any],
    ) -> bool:
        await self._owned(principal, session_id, cwd=None)
        return await self._repository.append(session_id, seq, kind, payload)

    async def events(
        self,
        principal: HubPrincipal,
        session_id: str,
        *,
        after: int,
        limit: int,
        cwd: str | None,
    ) -> tuple[SessionEvent, ...]:
        await self._owned(principal, session_id, cwd=cwd)
        return await self._repository.events_after(session_id, after, limit)

    async def list(
        self, principal: HubPrincipal, *, cwd: str | None, cursor: str | None, limit: int
    ) -> tuple[tuple[SessionRecord, ...], str | None]:
        self._authorise(principal)
        after = self.decode(cursor) if cursor is not None else None
        # One more than the page: whether a next page exists is known without an empty one.
        found = await self._repository.list(principal.name, cwd=cwd, cursor=after, limit=limit + 1)
        page = found[:limit]
        if len(found) <= limit:
            return page, None
        return page, self.encode(page[-1].updated_at, page[-1].session_id)

    @staticmethod
    def encode(updated_at: datetime, session_id: str) -> str:
        raw = f"{updated_at.isoformat()}{_SEPARATOR}{session_id}".encode()
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def decode(cursor: str) -> tuple[datetime, str]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode()
            stamp, _, session_id = raw.rpartition(_SEPARATOR)
            updated_at = datetime.fromisoformat(stamp)
        except (UnicodeError, binascii.Error, ValueError) as exc:
            raise InvalidSessionCursor("that cursor is not one the hub gave out") from exc
        if updated_at.tzinfo is None or SESSION_ID_SHAPE.fullmatch(session_id) is None:
            raise InvalidSessionCursor("that cursor is not one the hub gave out")
        return updated_at, session_id

    async def _owned(self, principal: HubPrincipal, session_id: str, *, cwd: str | None) -> None:
        self._authorise(principal)
        kept = await self._repository.owner(session_id)
        if kept is None or kept[0] != principal.name or (cwd is not None and kept[1] != cwd):
            raise self._unknown(session_id)

    def _authorise(self, principal: HubPrincipal) -> None:
        if not self._policy.permits(principal.scopes, HubAction.RECORD_ACP_SESSION):
            raise HubForbidden(f"{principal.name} may not keep ACP sessions")

    @staticmethod
    def _unknown(session_id: str) -> HubForbidden:
        return HubForbidden(f"no session {session_id} of yours under that folder")
