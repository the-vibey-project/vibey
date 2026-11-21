# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's ACP session routes (SP-ACP Task 6): offered only with a session service, reached as
the agent principal, each session kept to the principal that created it.

Over the real `AcpSessionService` and an in-memory repository: the SQL is held in
tests/infrastructure/db/test_acp_session_repository.py.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from vibey.application.acp.acp_session_service import AcpSessionService
from vibey.application.acp.dto import SessionEvent, SessionRecord, SessionSummary
from vibey.application.dto import HubPrincipal
from vibey.domain.acp.session_log import AcpSessionLimitReached, SessionEventConflict
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HUB_SCOPES, HubScope
from vibey.infrastructure.hub.app import HubAppFactory
from vibey.infrastructure.hub.authenticator import (
    AgentTokenAuthenticator,
    FirstOf,
    HubRequest,
    LocalTokenAuthenticator,
)

TOKEN = "t0ken"
AGENT_TOKEN = "ag3nt"
HOST = "127.0.0.1:8765"
HOST_AUTH = {"authorization": f"Bearer {TOKEN}", "host": HOST}
AGENT = {"authorization": f"Bearer {AGENT_TOKEN}", "host": HOST}
SID = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"
OTHER = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a02"
ROUTE = "/api/v1/acp/sessions"
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


class Repository:
    """Sessions and logs in memory; every listed session was last updated at `NOW`."""

    def __init__(self) -> None:
        self.sessions: dict[str, tuple[str, str]] = {}
        self.logs: dict[str, dict[int, tuple[str, dict[str, Any]]]] = {}

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
        if seq in log and log[seq] != (kind, dict(payload)):
            raise SessionEventConflict(f"session {session_id} already holds seq {seq}")
        if seq not in log and len(log) >= limit:
            raise AcpSessionLimitReached(f"session {session_id} holds all the hub keeps")
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
        mine = sorted(
            (sid for sid, (owner, folder) in self.sessions.items() if owner == created_by),
            reverse=True,
        )
        records = [
            SessionRecord(
                session_id=sid,
                cwd=self.sessions[sid][1],
                title=None,
                updated_at=NOW,
                closed=any(kind == "closed" for kind, _ in self.logs[sid].values()),
            )
            for sid in mine
            if cwd is None or self.sessions[sid][1] == cwd
        ]
        if cursor is not None:
            records = [r for r in records if (r.updated_at, r.session_id) < cursor]
        return tuple(records[:limit])

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


class Blind:
    """Names a principal that holds no `view`."""

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        return HubPrincipal(name="agent", scopes=frozenset({HubScope.ANSWER}))


class Viewer:
    """Names a read-only paired device: `view` and nothing else."""

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        return HubPrincipal(name="agent", scopes=frozenset({HubScope.VIEW}))


class Quiet:
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def subscribe(self, project_id: Any) -> Any:  # no live route is used here
        raise AssertionError


def _app(
    *, sessions: bool = True, authenticator: Any = None, **caps: int
) -> tuple[FastAPI, Repository]:
    repository = Repository()

    async def ready() -> bool:
        return True

    app = HubAppFactory().build(
        None,  # type: ignore[arg-type] -- no other route is called here
        authenticator=authenticator
        or FirstOf(
            [
                LocalTokenAuthenticator(TOKEN),
                AgentTokenAuthenticator(AGENT_TOKEN, AGENT_DEFAULT_SCOPES),
            ]
        ),
        allowed_hosts=HUB_BINDING.allowed_hosts(8765, frozenset()),
        ready=ready,
        live=Quiet(),  # type: ignore[arg-type]
        acp_sessions=AcpSessionService(repository, HUB_SCOPES, **caps) if sessions else None,
    )
    return app, repository


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=f"http://{HOST}")


async def test_routes_absent_without_acp_sessions() -> None:
    app, _ = _app(sessions=False)
    async with _client(app) as client:
        answers = [
            await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"}),
            await client.get(ROUTE, headers=AGENT),
            await client.post(
                f"{ROUTE}/{SID}/events",
                headers=AGENT,
                json={"seq": 1, "kind": "plan", "payload": {}},
            ),
            await client.get(f"{ROUTE}/{SID}/events", headers=AGENT),
        ]
    assert [answer.status_code for answer in answers] == [404, 404, 404, 404]
    assert not any(path.startswith(ROUTE) for path in app.openapi()["paths"])


async def test_agent_principal_can_create_append_list_and_read() -> None:
    app, repository = _app()
    async with _client(app) as client:
        created = await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        again = await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        stored = [
            await client.post(
                f"{ROUTE}/{SID}/events",
                headers=AGENT,
                json={"seq": seq, "kind": kind, "payload": payload},
            )
            for seq, kind, payload in (
                (1, "user_message", {"text": "hi"}),
                (2, "closed", {}),
                (2, "closed", {}),  # a resend: answered as stored
            )
        ]
        listed = await client.get(ROUTE, headers=AGENT, params={"cwd": "/work"})
        read = await client.get(f"{ROUTE}/{SID}/events", headers=AGENT, params={"after": 1})
        empty = await client.get(f"{ROUTE}/{SID}/events", headers=AGENT, params={"after": 9})
    assert (created.status_code, created.json()) == (201, {"session_id": SID})
    assert again.status_code == 201
    assert [(r.status_code, r.json()) for r in stored] == [(200, {"stored": True})] * 3
    assert listed.json() == {
        "sessions": [
            {
                "session_id": SID,
                "cwd": "/work",
                "title": None,
                "updated_at": NOW.isoformat(),
                "closed": True,
            }
        ],
        "next_cursor": None,
    }
    assert read.json() == {"events": [{"seq": 2, "kind": "closed", "payload": {}}], "last_seq": 2}
    assert empty.json() == {"events": [], "last_seq": None}
    assert repository.sessions == {SID: ("agent", "/work")}


async def test_conflicting_append_is_409() -> None:
    app, repository = _app()
    async with _client(app) as client:
        await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        await client.post(
            f"{ROUTE}/{SID}/events", headers=AGENT, json={"seq": 1, "kind": "plan", "payload": {}}
        )
        conflict = await client.post(
            f"{ROUTE}/{SID}/events",
            headers=AGENT,
            json={"seq": 1, "kind": "plan", "payload": {"entries": []}},
        )
        folder = await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/b"})
    assert conflict.status_code == 409 and "seq 1" in conflict.json()["detail"]
    assert folder.status_code == 409
    assert repository.logs[SID] == {1: ("plan", {})}


async def test_another_principal_reads_nothing_and_learns_nothing() -> None:
    app, repository = _app()
    async with _client(app) as client:
        await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        theirs = await client.get(f"{ROUTE}/{SID}/events", headers=HOST_AUTH)
        missing = await client.get(f"{ROUTE}/{OTHER}/events", headers=HOST_AUTH)
        folder = await client.get(
            f"{ROUTE}/{SID}/events", headers=AGENT, params={"cwd": "/elsewhere"}
        )
        forged = await client.post(
            f"{ROUTE}/{SID}/events",
            headers=HOST_AUTH,
            json={"seq": 1, "kind": "agent_message", "payload": {"text": "forged"}},
        )
        listed = await client.get(ROUTE, headers=HOST_AUTH)
    assert [r.status_code for r in (theirs, missing, folder, forged)] == [403] * 4
    assert theirs.json()["detail"] == missing.json()["detail"].replace(OTHER, SID)
    assert listed.json() == {"sessions": [], "next_cursor": None}
    assert repository.logs[SID] == {}


async def test_a_principal_without_view_is_refused() -> None:
    app, _ = _app(authenticator=Blind())
    async with _client(app) as client:
        answer = await client.get(ROUTE, headers=AGENT)
    assert answer.status_code == 403 and "may not read ACP sessions" in answer.json()["detail"]


async def test_a_read_only_device_may_read_but_never_create_or_append() -> None:
    """`view` is a read: a paired device holding only it never makes the hub keep anything."""
    app, repository = _app(authenticator=Viewer())
    await repository.create(SID, "/work", "agent", limit=9)
    async with _client(app) as client:
        created = await client.post(ROUTE, headers=AGENT, json={"session_id": OTHER, "cwd": "/w"})
        appended = await client.post(
            f"{ROUTE}/{SID}/events",
            headers=AGENT,
            json={"seq": 1, "kind": "agent_message", "payload": {"text": "forged"}},
        )
        listed = await client.get(ROUTE, headers=AGENT)
        read = await client.get(f"{ROUTE}/{SID}/events", headers=AGENT)
    assert [created.status_code, appended.status_code] == [403, 403]
    assert "may not keep ACP sessions" in created.json()["detail"]
    assert [listed.status_code, read.status_code] == [200, 200]
    assert set(repository.sessions) == {SID} and repository.logs[SID] == {}


async def test_past_the_caps_a_write_is_507_and_nothing_kept_changes() -> None:
    app, repository = _app(sessions_max=1, session_events_max=1)
    async with _client(app) as client:
        await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        second = await client.post(ROUTE, headers=AGENT, json={"session_id": OTHER, "cwd": "/w"})
        event = {"seq": 1, "kind": "plan", "payload": {}}
        first = await client.post(f"{ROUTE}/{SID}/events", headers=AGENT, json=event)
        full = await client.post(f"{ROUTE}/{SID}/events", headers=AGENT, json={**event, "seq": 2})
    assert (first.status_code, second.status_code, full.status_code) == (200, 507, 507)
    assert "sessions_max" in second.json()["detail"]
    assert set(repository.sessions) == {SID} and repository.logs[SID] == {1: ("plan", {})}


async def test_a_request_that_proves_nothing_is_refused() -> None:
    app, _ = _app()
    async with _client(app) as client:
        answer = await client.get(ROUTE, headers={"host": HOST})
    assert answer.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", ROUTE, {"session_id": "s", "cwd": "/work"}),
        ("POST", ROUTE, {"session_id": SID.upper(), "cwd": "/work"}),
        ("POST", ROUTE, {"session_id": SID, "cwd": "relative"}),
        ("POST", ROUTE, {"session_id": SID, "cwd": "/" + "x" * 5000}),
        ("POST", ROUTE, {"session_id": SID, "cwd": "/work", "owner": "host"}),
        ("POST", f"{ROUTE}/{SID}/events", {"seq": 0, "kind": "plan", "payload": {}}),
        ("POST", f"{ROUTE}/{SID}/events", {"seq": 2**63, "kind": "plan", "payload": {}}),
        ("POST", f"{ROUTE}/{SID}/events", {"seq": 1, "kind": "request_permission", "payload": {}}),
        ("POST", f"{ROUTE}/{SID}/events", {"seq": 1, "kind": "plan", "payload": []}),
        ("POST", f"{ROUTE}/s/events", {"seq": 1, "kind": "plan", "payload": {}}),
        ("GET", f"{ROUTE}/..%2Fetc/events", None),
        ("GET", f"{ROUTE}/{SID}/events?after=-1", None),
        ("GET", f"{ROUTE}/{SID}/events?limit=201", None),
        ("GET", f"{ROUTE}?limit=0", None),
        ("GET", f"{ROUTE}?cursor=not-one", None),
    ],
)
async def test_a_malformed_request_is_refused_before_anything_is_kept(
    method: str, path: str, body: Any
) -> None:
    app, repository = _app()
    async with _client(app) as client:
        answer = await client.request(method, path, headers=AGENT, json=body)
    assert answer.status_code in (404, 422), answer.text
    assert repository.sessions == {}


async def test_the_list_pages_with_its_cursor() -> None:
    app, _ = _app()
    ids = [f"00000000-0000-4000-8000-{n:012d}" for n in range(1, 6)]
    async with _client(app) as client:
        for sid in ids:
            await client.post(ROUTE, headers=AGENT, json={"session_id": sid, "cwd": "/work"})
        first = (await client.get(ROUTE, headers=AGENT, params={"limit": 3})).json()
        second = (
            await client.get(
                ROUTE, headers=AGENT, params={"limit": 3, "cursor": first["next_cursor"]}
            )
        ).json()
    assert [s["session_id"] for s in first["sessions"]] == ids[::-1][:3]
    assert [s["session_id"] for s in second["sessions"]] == ids[::-1][3:]
    assert second["next_cursor"] is None


async def test_the_routes_are_documented_under_acp() -> None:
    app, _ = _app()
    paths = app.openapi()["paths"]
    assert set(paths[ROUTE]) == {"get", "post"}
    assert set(paths[f"{ROUTE}/{{session_id}}/events"]) == {"get", "post"}
    assert {paths[ROUTE]["post"]["tags"][0], paths[ROUTE]["get"]["tags"][0]} == {"acp"}


async def test_the_summary_route_reads_newest_seq_and_states() -> None:
    app, _ = _app()
    async with _client(app) as client:
        await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": "/work"})
        for seq, kind, payload in ((1, "attach", {"projectId": "p"}), (2, "title", {"title": "t"})):
            await client.post(
                f"{ROUTE}/{SID}/events",
                headers=AGENT,
                json={"seq": seq, "kind": kind, "payload": payload},
            )
        summary = await client.get(f"{ROUTE}/{SID}", headers=AGENT, params={"cwd": "/work"})
        elsewhere = await client.get(f"{ROUTE}/{SID}", headers=AGENT, params={"cwd": "/b"})
        theirs = await client.get(f"{ROUTE}/{SID}", headers=HOST_AUTH)
    assert summary.json() == {
        "session_id": SID,
        "newest_seq": 2,
        "mode": None,
        "attach": {"projectId": "p"},
        "title": {"title": "t"},
    }
    assert (elsewhere.status_code, theirs.status_code) == (403, 403)


@pytest.mark.parametrize("cwd", ["/work\u202eevil", "/a\nb", "/a\x1b[31m", "/a\u2028b"])
async def test_a_folder_with_a_character_that_is_not_printable_is_refused(cwd: str) -> None:
    app, repository = _app()
    async with _client(app) as client:
        answer = await client.post(ROUTE, headers=AGENT, json={"session_id": SID, "cwd": cwd})
    assert answer.status_code == 422 and repository.sessions == {}
