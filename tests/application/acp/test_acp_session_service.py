# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub keeps each ACP session for the principal that created it (SP-ACP Task 6).

Over an in-memory repository: the authorisation and ownership rules are the service's; the
SQL is held in tests/infrastructure/db/test_acp_session_repository.py.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import base64
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from vibey.application.acp.acp_session_service import AcpSessionService
from vibey.application.acp.dto import SessionEvent, SessionRecord, SessionSummary
from vibey.application.acp.interfaces.acp_session_service_interface import (
    AcpSessionServiceInterface,
)
from vibey.application.dto import HubPrincipal
from vibey.domain.acp.session_log import (
    AcpSessionLimitReached,
    InvalidSessionCursor,
    SessionEventConflict,
)
from vibey.domain.hub_scope import HUB_SCOPES, HubForbidden, HubScope

AGENT = HubPrincipal(
    name="agent", scopes=frozenset({HubScope.VIEW, HubScope.ANSWER, HubScope.ACP_SESSIONS})
)
PHONE = HubPrincipal(name="phone", scopes=frozenset({HubScope.VIEW, HubScope.ACP_SESSIONS}))
VIEWER = HubPrincipal(name="viewer", scopes=frozenset({HubScope.VIEW}))
"""A read-only paired device: it may look, never write."""
BLIND = HubPrincipal(name="blind", scopes=frozenset({HubScope.ANSWER, HubScope.RUN}))
SID = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"
OTHER = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a02"
THIRD = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a03"
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


class Repository:
    """Sessions and logs in memory, recording what it was asked."""

    def __init__(self) -> None:
        self.sessions: dict[str, tuple[str, str]] = {}
        self.logs: dict[str, dict[int, tuple[str, dict[str, Any]]]] = {}
        self.listed: list[tuple[str, str | None, tuple[datetime, str] | None, int]] = []
        self.records: tuple[SessionRecord, ...] = ()

    async def create(self, session_id: str, cwd: str, created_by: str, *, limit: int) -> bool:
        held = sum(1 for owner, _ in self.sessions.values() if owner == created_by)
        if session_id in self.sessions or held >= limit:
            return False
        self.sessions[session_id] = (created_by, cwd)
        self.logs[session_id] = {}
        return True

    async def append(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any], *, limit: int
    ) -> bool:
        log = self.logs[session_id]
        if seq in log:
            if log[seq] != (kind, dict(payload)):
                raise SessionEventConflict(f"seq {seq} is taken")
            return True
        if len(log) >= limit:
            raise AcpSessionLimitReached(f"session {session_id} is full")
        log[seq] = (kind, dict(payload))
        return True

    async def events_after(
        self, session_id: str, after: int, limit: int
    ) -> tuple[SessionEvent, ...]:
        log = self.logs[session_id]
        return tuple(SessionEvent(seq, *log[seq]) for seq in sorted(log) if seq > after)[:limit]

    async def list(
        self,
        created_by: str,
        *,
        cwd: str | None,
        cursor: tuple[datetime, str] | None,
        limit: int,
    ) -> tuple[SessionRecord, ...]:
        self.listed.append((created_by, cwd, cursor, limit))
        return self.records[:limit]

    async def owner(self, session_id: str) -> tuple[str, str] | None:
        return self.sessions.get(session_id)

    async def summary(self, session_id: str) -> SessionSummary:
        log = self.logs[session_id]

        def newest(kind: str) -> dict[str, Any] | None:
            return next(
                (log[seq][1] for seq in sorted(log, reverse=True) if log[seq][0] == kind), None
            )

        return SessionSummary(
            newest_seq=max(log, default=0),
            mode=newest("mode"),
            attach=newest("attach"),
            title=newest("title"),
        )


def _service(**caps: int) -> tuple[AcpSessionService, Repository]:
    repository = Repository()
    return AcpSessionService(repository, HUB_SCOPES, **caps), repository


def test_the_service_meets_its_declared_seam() -> None:
    assert isinstance(_service()[0], AcpSessionServiceInterface)


async def test_the_creator_can_create_append_and_read() -> None:
    service, repository = _service()
    await service.create(AGENT, SID, "/work")
    await service.create(AGENT, SID, "/work")  # again: nothing changes
    assert await service.append(AGENT, SID, 1, "user_message", {"text": "hi"}) is True
    events = await service.events(AGENT, SID, after=0, limit=10, cwd="/work")
    assert [(e.seq, e.kind) for e in events] == [(1, "user_message")]
    assert await service.events(AGENT, SID, after=0, limit=10, cwd=None) == events
    assert repository.sessions == {SID: ("agent", "/work")}


async def test_another_principal_cannot_read_or_append() -> None:
    service, repository = _service()
    await service.create(AGENT, SID, "/work")
    await service.append(AGENT, SID, 1, "user_message", {"text": "secret"})
    with pytest.raises(HubForbidden) as read:
        await service.events(PHONE, SID, after=0, limit=10, cwd="/work")
    with pytest.raises(HubForbidden) as write:
        await service.append(PHONE, SID, 2, "agent_message", {"text": "forged"})
    with pytest.raises(HubForbidden):
        await service.create(PHONE, SID, "/work")
    assert len(repository.logs[SID]) == 1
    # Said exactly as for a session that does not exist: a guessed id learns nothing.
    other = "1" * 8 + SID[8:]
    with pytest.raises(HubForbidden) as missing:
        await service.events(PHONE, other, after=0, limit=10, cwd="/work")
    assert str(read.value) == str(write.value)
    assert str(missing.value) == str(read.value).replace(SID, other)


async def test_a_read_naming_another_folder_is_refused_as_unknown() -> None:
    service, _ = _service()
    await service.create(AGENT, SID, "/work/a")
    with pytest.raises(HubForbidden, match="no session"):
        await service.events(AGENT, SID, after=0, limit=10, cwd="/work/b")


async def test_creating_a_kept_session_under_another_folder_is_a_conflict() -> None:
    service, repository = _service()
    await service.create(AGENT, SID, "/work/a")
    with pytest.raises(SessionEventConflict, match="another folder"):
        await service.create(AGENT, SID, "/work/b")
    assert repository.sessions[SID] == ("agent", "/work/a")


async def test_appending_to_a_session_never_created_is_refused() -> None:
    service, repository = _service()
    with pytest.raises(HubForbidden, match="no session"):
        await service.append(AGENT, SID, 1, "plan", {})
    assert repository.logs == {}


async def test_a_principal_without_view_or_acp_sessions_is_refused_before_any_read() -> None:
    service, repository = _service()
    await repository.create(SID, "/work", "blind", limit=9)
    calls = [
        (service.create(BLIND, SID, "/work"), "may not keep ACP sessions"),
        (service.append(BLIND, SID, 1, "plan", {}), "may not keep ACP sessions"),
        (service.events(BLIND, SID, after=0, limit=1, cwd=None), "may not read ACP sessions"),
        (service.list(BLIND, cwd=None, cursor=None, limit=1), "may not read ACP sessions"),
    ]
    for call, refusal in calls:
        with pytest.raises(HubForbidden, match=refusal):
            await call
    assert repository.listed == [] and repository.logs[SID] == {}


async def test_a_read_only_device_may_look_but_never_create_or_append() -> None:
    """`view` alone is a read: it never makes the hub keep anything (security review)."""
    service, repository = _service()
    with pytest.raises(HubForbidden, match="may not keep ACP sessions"):
        await service.create(VIEWER, SID, "/work")
    await repository.create(SID, "/work", "viewer", limit=9)
    with pytest.raises(HubForbidden, match="may not keep ACP sessions"):
        await service.append(VIEWER, SID, 1, "agent_message", {"text": "x"})
    assert await service.events(VIEWER, SID, after=0, limit=9, cwd=None) == ()
    assert await service.list(VIEWER, cwd=None, cursor=None, limit=9) == ((), None)
    assert repository.logs[SID] == {}


async def test_past_sessions_max_a_new_session_is_refused_and_nothing_kept_changes() -> None:
    service, repository = _service(sessions_max=2)
    await service.create(AGENT, SID, "/work")
    await service.create(AGENT, OTHER, "/work")
    with pytest.raises(AcpSessionLimitReached, match=r"sessions_max"):
        await service.create(AGENT, THIRD, "/work")
    await service.create(AGENT, SID, "/work")  # one already kept: still a no-op at the cap
    await service.create(PHONE, THIRD, "/work")  # the cap is each principal's own
    assert set(repository.sessions) == {SID, OTHER, THIRD}
    assert repository.sessions[THIRD] == ("phone", "/work")


async def test_past_session_events_max_an_append_is_refused_and_nothing_kept_changes() -> None:
    service, repository = _service(session_events_max=2)
    await service.create(AGENT, SID, "/work")
    await service.append(AGENT, SID, 1, "user_message", {"text": "a"})
    await service.append(AGENT, SID, 2, "agent_message", {"text": "b"})
    with pytest.raises(AcpSessionLimitReached):
        await service.append(AGENT, SID, 3, "closed", {})
    # A resend of what is kept is still answered as stored.
    assert await service.append(AGENT, SID, 2, "agent_message", {"text": "b"}) is True
    assert repository.logs[SID] == {
        1: ("user_message", {"text": "a"}),
        2: ("agent_message", {"text": "b"}),
    }


async def test_a_conflicting_append_is_refused_and_nothing_is_overwritten() -> None:
    service, repository = _service()
    await service.create(AGENT, SID, "/work")
    await service.append(AGENT, SID, 1, "plan", {"entries": []})
    with pytest.raises(SessionEventConflict):
        await service.append(AGENT, SID, 1, "plan", {"entries": [1]})
    assert repository.logs[SID][1] == ("plan", {"entries": []})


def _record(n: int) -> SessionRecord:
    return SessionRecord(
        session_id=f"00000000-0000-4000-8000-{n:012d}",
        cwd="/work",
        title=None,
        updated_at=NOW - timedelta(minutes=n),
        closed=False,
    )


async def test_list_pages_with_an_opaque_cursor_from_the_last_record() -> None:
    service, repository = _service()
    repository.records = tuple(_record(n) for n in range(1, 4))
    page, cursor = await service.list(AGENT, cwd="/work", cursor=None, limit=2)
    assert page == repository.records[:2]
    assert cursor is not None
    assert repository.listed == [("agent", "/work", None, 3)]  # one more, to know of a next page
    assert service.decode(cursor) == (_record(2).updated_at, _record(2).session_id)
    assert base64.urlsafe_b64decode(cursor).decode() == (
        f"{_record(2).updated_at.isoformat()}|{_record(2).session_id}"
    )
    await service.list(AGENT, cwd=None, cursor=cursor, limit=2)
    assert repository.listed[-1] == ("agent", None, service.decode(cursor), 3)


async def test_the_last_page_has_no_cursor() -> None:
    service, repository = _service()
    repository.records = (_record(1), _record(2))
    assert await service.list(AGENT, cwd=None, cursor=None, limit=2) == (repository.records, None)


@pytest.mark.parametrize(
    "cursor",
    [
        "not base64!",
        base64.urlsafe_b64encode(b"\xff\xfe").decode(),
        base64.urlsafe_b64encode(b"yesterday|" + SID.encode()).decode(),
        base64.urlsafe_b64encode(b"2026-11-21T12:00:00|" + SID.encode()).decode(),
        base64.urlsafe_b64encode(b"2026-11-21T12:00:00+00:00|../etc").decode(),
        "é",
    ],
)
async def test_a_cursor_the_hub_never_gave_is_refused(cursor: str) -> None:
    service, repository = _service()
    with pytest.raises(InvalidSessionCursor):
        await service.list(AGENT, cwd=None, cursor=cursor, limit=2)
    assert repository.listed == []


async def test_a_summary_is_a_read_of_the_creators_session_under_its_folder() -> None:
    service, _ = _service()
    await service.create(AGENT, SID, "/work")
    await service.append(AGENT, SID, 1, "mode", {"modeId": "observe"})
    await service.append(AGENT, SID, 2, "user_message", {"text": "hi"})
    summary = await service.summary(VIEWER_OF_AGENT, SID, cwd="/work")
    assert summary == SessionSummary(
        newest_seq=2, mode={"modeId": "observe"}, attach=None, title=None
    )
    for principal, cwd in ((PHONE, "/work"), (AGENT, "/elsewhere"), (BLIND, None)):
        with pytest.raises(HubForbidden):
            await service.summary(principal, SID, cwd=cwd)


VIEWER_OF_AGENT = HubPrincipal(name="agent", scopes=frozenset({HubScope.VIEW}))
"""The agent principal narrowed to `view`: it may still read its own sessions back."""
