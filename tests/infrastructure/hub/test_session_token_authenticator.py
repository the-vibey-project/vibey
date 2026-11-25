# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub accepts an engine session's token for web search and fetch and nothing else, and
charges each call to the session's own cap and to the agent's hourly bucket (SP-LOOPS Phase 6,
Task 3; R2).

The authenticator alone first, then the whole matrix in an in-process app: sessions are minted
for real (`SessionWebPrincipals` over the real token files and the real state-folder registry,
with a fixed token source), the hub's other routes run over the real `HubService` whose
collaborators fail the test if anything reaches them, and search and fetch are fakes. The clock
is injected; nothing sleeps, nothing reaches a network. File modes are POSIX, so the module is
skipped elsewhere. Module-level test functions rather than a class with an interface beside it
(ADR-0016)."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vibey.application.dto import HubPrincipal, SessionGrant, WebHit, WebPage, WebSearchAnswer
from vibey.application.hub.hub_service import HubService
from vibey.application.hub.web_tools_service import WebToolsService
from vibey.application.session_token_lookup import SessionTokenLookup
from vibey.application.session_web_principals import SessionWebPrincipals
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.domain.ledger import EventKind
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.web_tools import WebTarget, WebToolSettings
from vibey.infrastructure.hub.app import POLICY_VIOLATION, WEB_ROUTES, HubAppFactory
from vibey.infrastructure.hub.authenticator import (
    AgentTokenAuthenticator,
    FirstOf,
    HubRequest,
    LocalTokenAuthenticator,
)
from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)
from vibey.infrastructure.hub.session_registry import SessionRegistry
from vibey.infrastructure.hub.session_token_authenticator import SessionTokenAuthenticator
from vibey.infrastructure.hub.session_token_store import SessionTokenStore

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")

HOST_TOKEN = "h0st-t0ken"
AGENT_TOKEN = "ag3nt-t0ken"
HOST = "127.0.0.1:8765"
SEARCH = f"{WEB_ROUTES}search"
FETCH = f"{WEB_ROUTES}fetch"
RUN_A = UUID("00000000-0000-4000-8000-00000000000a")
RUN_B = UUID("00000000-0000-4000-8000-00000000000b")
TOKEN_A = "sess-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_B = "sess-BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
DEADLINE = timedelta(hours=1)
NOW = 1_800_000_000.0
PID = "11111111-1111-4111-8111-111111111111"


# -- fakes ---------------------------------------------------------------------------------------


class _Clock:
    """The hub's wall clock, which a session's expiry is read against."""

    def __init__(self, now: float = NOW) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _Logger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))


class _Lookup:
    def __init__(
        self, principal: SessionPrincipal | None = None, error: Exception | None = None
    ) -> None:
        self.principal = principal
        self.error = error
        self.asked: list[tuple[str, float]] = []

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        self.asked.append((token, now))
        if self.error is not None:
            raise self.error
        return self.principal


class _Tokens:
    def __init__(self, *tokens: str) -> None:
        self._tokens = list(tokens)

    def token(self) -> str:
        return self._tokens.pop(0)


class _Search:
    def __init__(self) -> None:
        self.asked: list[str] = []

    async def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        self.asked.append(query)
        return WebSearchAnswer(hits=(WebHit("T", "https://t.example/", "S"),), backend="searxng")


class _Fetch:
    def __init__(self) -> None:
        self.asked: list[WebTarget] = []

    async def fetch(
        self, target: WebTarget, settings: WebToolSettings, reached: list[str] | None = None
    ) -> WebPage:
        self.asked.append(target)
        return WebPage(
            url=target.url,
            hosts=(target.host,),
            title="Docs",
            text="Body.",
            truncated=False,
            content_type="text/html",
        )


class _Audit:
    def __init__(self) -> None:
        self.records: list[tuple[EventKind, dict[str, object]]] = []

    async def ready(self, project_id: UUID | None) -> None:
        return None

    async def record(
        self, kind: EventKind, payload: Mapping[str, object], at: datetime, project_id: UUID | None
    ) -> int:
        self.records.append((kind, dict(payload)))
        return 1


class _Untouched:
    """A collaborator of the hub's other routes: reaching it fails the test, because a session
    must be refused before anything is read or changed."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"a session reached {name}")


class _Quiet:
    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    @contextmanager
    def subscribe(self, project_id: UUID) -> Iterator[Any]:
        raise AssertionError("a session subscribed to a live feed")
        yield  # pragma: no cover - never reached


@dataclass
class _Hub:
    app: FastAPI
    principals: SessionWebPrincipals
    clock: _Clock
    search: _Search
    fetch: _Fetch
    audit: _Audit
    folders: Path

    def mint(self, run: UUID) -> SessionGrant:
        folder = self.folders / str(run)
        folder.mkdir()
        os.chmod(folder, 0o700)
        return self.principals.mint(run, folder, self.clock())

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url=f"http://{HOST}"
        )


def _bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}", "host": HOST}


def _hub(tmp_path: Path, settings: WebToolSettings | None = None) -> _Hub:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    folders = tmp_path / "runs"
    folders.mkdir(mode=0o700)
    clock = _Clock()
    registry = SessionRegistry(state)
    principals = SessionWebPrincipals(
        tokens=_Tokens(TOKEN_A, TOKEN_B),
        files=SessionTokenStore(),
        registry=registry,
        run_deadline=DEADLINE,
    )
    search, fetch, audit = _Search(), _Fetch(), _Audit()
    web = WebToolsService(
        search=search,
        fetch=fetch,
        audit=audit,
        settings=settings or WebToolSettings(),
        clock=lambda: 1_000.0,
        now=lambda: datetime(2026, 11, 24, tzinfo=UTC),
        nonce=lambda: "n0nce",
    )
    untouched = cast(Any, _Untouched())
    service = HubService(
        projects=untouched,
        gates=untouched,
        gate_lookup=untouched,
        gate_answers=untouched,
        budgets=untouched,
        queue=untouched,
        ledger=untouched,
        ledger_range=untouched,
        documents=untouched,
        probes=untouched,
        lifecycle=untouched,
    )

    async def ready() -> bool:
        return True

    app = HubAppFactory().build(
        service,
        authenticator=FirstOf(
            [
                LocalTokenAuthenticator(HOST_TOKEN),
                AgentTokenAuthenticator(AGENT_TOKEN, AGENT_DEFAULT_SCOPES),
                SessionTokenAuthenticator(SessionTokenLookup(registry), clock=clock),
            ]
        ),
        allowed_hosts=HUB_BINDING.allowed_hosts(8765, frozenset()),
        ready=ready,
        live=_Quiet(),  # type: ignore[arg-type]
        pairing=untouched,
        workflows=untouched,
        runs=untouched,
        acp_sessions=untouched,
        web=web,
    )
    return _Hub(app, principals, clock, search, fetch, audit, folders)


# -- the authenticator alone ---------------------------------------------------------------------


def _request(headers: dict[str, str]) -> HubRequest:
    return HubRequest(method="POST", path=SEARCH, query="", headers=headers, body=b"")


PRINCIPAL = SessionPrincipal(name=f"session:{RUN_A}", run_id=RUN_A, expires_at=NOW + 60)


def test_the_authenticator_meets_its_declared_seam() -> None:
    assert isinstance(
        SessionTokenAuthenticator(_Lookup(), clock=_Clock()), HubAuthenticatorInterface
    )


async def test_a_session_token_names_a_web_only_session_principal_at_the_hubs_now() -> None:
    lookup = _Lookup(PRINCIPAL)
    clock = _Clock(NOW + 5)
    found = await SessionTokenAuthenticator(lookup, clock=clock).authenticate(
        _request({"authorization": f"Bearer  {TOKEN_A} "})
    )
    assert found == HubPrincipal(name=f"session:{RUN_A}", scopes=frozenset({HubScope.WEB}))
    assert lookup.asked == [(TOKEN_A, NOW + 5)]


@pytest.mark.parametrize(
    "headers",
    [{}, {"authorization": f"Basic {TOKEN_A}"}, {"authorization": "Bearer "}, {"x": TOKEN_A}],
)
async def test_a_request_with_no_bearer_token_proves_nothing_and_asks_nothing(
    headers: dict[str, str],
) -> None:
    lookup = _Lookup(PRINCIPAL)
    assert (
        await SessionTokenAuthenticator(lookup, clock=_Clock()).authenticate(_request(headers))
        is None
    )
    assert lookup.asked == []


async def test_a_token_the_registry_does_not_know_proves_nothing() -> None:
    """Unknown, revoked or expired: the lookup's `None`, decided by the session policy's
    `expired` -- the authenticator holds no second copy of the expiry rule."""
    authenticator = SessionTokenAuthenticator(_Lookup(None), clock=_Clock())
    assert await authenticator.authenticate(_request({"authorization": "Bearer x"})) is None


@pytest.mark.parametrize(
    "error",
    [
        PermissionError("/state/sessions/ab12.json belongs to another account; refusing to use it"),
        ValueError("/state/sessions/ab12.json is not JSON"),
    ],
)
async def test_an_unreadable_registry_denies_and_is_logged_by_path_never_by_token(
    error: Exception,
) -> None:
    """A registry entry or folder that is not this account's own, or is malformed, can only
    deny, never grant: the token is treated as unknown (401) and the path is logged."""
    logger = _Logger()
    authenticator = SessionTokenAuthenticator(_Lookup(error=error), clock=_Clock(), logger=logger)
    found = await authenticator.authenticate(_request({"authorization": f"Bearer {TOKEN_A}"}))
    assert found is None
    assert len(logger.lines) == 1
    event, fields = logger.lines[0]
    assert event == "session_registry_unreadable"
    assert "/state/sessions/ab12.json" in fields["detail"]
    assert fields["error"] == type(error).__name__
    assert TOKEN_A not in repr(logger.lines)


async def test_an_unreadable_registry_with_no_logger_still_denies() -> None:
    authenticator = SessionTokenAuthenticator(
        _Lookup(error=PermissionError("/s/x.json")), clock=_Clock()
    )
    assert await authenticator.authenticate(_request({"authorization": "Bearer t"})) is None


async def test_any_other_failure_of_the_registry_is_not_swallowed() -> None:
    """Only the two refusals the registry names are read as "unknown"; a disk that fails is
    the hub's 500, never a silent pass or a silent deny."""
    authenticator = SessionTokenAuthenticator(
        _Lookup(error=OSError(5, "Input/output error")), clock=_Clock()
    )
    with pytest.raises(OSError, match="Input/output"):
        await authenticator.authenticate(_request({"authorization": "Bearer t"}))


async def test_a_real_registry_entry_that_is_not_owner_only_denies(tmp_path: Path) -> None:
    """The decided failure policy, over the real registry: an entry opened to other accounts
    is refused by the registry, and the hub reads it as an unknown token."""
    hub = _hub(tmp_path)
    grant = hub.mint(RUN_A)
    entry = tmp_path / "state" / "sessions" / f"{grant.digest}.json"
    os.chmod(entry, 0o644)
    logger = _Logger()
    authenticator = SessionTokenAuthenticator(
        SessionTokenLookup(SessionRegistry(tmp_path / "state")), clock=hub.clock, logger=logger
    )
    assert await authenticator.authenticate(_request(_bearer(TOKEN_A))) is None
    assert str(entry) in logger.lines[0][1]["detail"]
    assert TOKEN_A not in repr(logger.lines)
    async with hub.client() as client:
        refused = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
    assert refused.status_code == 401 and hub.search.asked == []


# -- what a session token reaches ----------------------------------------------------------------


async def test_a_session_token_searches_and_fetches_the_web(tmp_path: Path) -> None:
    hub = _hub(tmp_path)
    hub.mint(RUN_A)
    async with hub.client() as client:
        found = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
        page = await client.post(
            FETCH, headers=_bearer(TOKEN_A), json={"url": "https://docs.example/"}
        )
    assert found.status_code == 200 and found.json()["results"][0]["url"] == "https://t.example/"
    assert page.status_code == 200 and page.json()["url"] == "https://docs.example/"
    assert [p["principal"] for _, p in hub.audit.records] == [f"session:{RUN_A}"] * 2
    assert TOKEN_A not in repr(hub.audit.records)


async def test_a_session_token_is_refused_403_by_a_view_route_and_a_write_route(
    tmp_path: Path,
) -> None:
    """A valid token on the wrong route is a 403 (it proved who it is; it may not do this),
    never a 401, and nothing behind the route is reached."""
    hub = _hub(tmp_path)
    hub.mint(RUN_A)
    async with hub.client() as client:
        viewed = await client.get("/api/v1/projects", headers=_bearer(TOKEN_A))
        answered = await client.post(
            f"/api/v1/gates/{PID}/answer", headers=_bearer(TOKEN_A), json={"answer": "yes"}
        )
    assert (viewed.status_code, answered.status_code) == (403, 403)
    assert "web" in viewed.json()["detail"]
    assert TOKEN_A not in viewed.text + answered.text


def _calls(app: FastAPI) -> list[tuple[str, str]]:
    """Every HTTP route the app has, as (method, a path with its parameters filled in)."""
    filled = {"project_id": PID, "gate_id": PID, "job_id": PID}
    calls: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = re.sub(
            r"\{(\w+)\}",
            lambda m: filled.get(m.group(1), "00000000-0000-4000-8000-000000000001"),
            route.path,
        )
        calls.extend((method, path) for method in sorted(route.methods or ()))
    return calls


async def test_every_route_that_needs_a_principal_refuses_a_session_403_but_the_web_two(
    tmp_path: Path,
) -> None:
    """Every route a caller who proves nothing is refused (401) -- the routes that act for a
    principal -- refuses a session's token with 403, except search and fetch. The hub is built
    with every optional surface (pairing, workflows, ACP sessions, web), so none is missed, and
    any future route is held to the same rule."""
    hub = _hub(tmp_path)
    hub.mint(RUN_A)
    seen: dict[tuple[str, str], int] = {}
    async with hub.client() as client:
        for number, (method, path) in enumerate(_calls(hub.app)):
            # Each anonymous probe from its own address, so none draws down another's
            # failed-authentication bucket.
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=hub.app, client=(f"10.0.0.{number + 1}", 1)),
                base_url=f"http://{HOST}",
            ) as stranger:
                anonymous = await stranger.request(method, path, headers={"host": HOST}, json={})
            if anonymous.status_code != 401:
                continue  # the landing page, health, a pairing claim: no principal is asked
            answer = await client.request(method, path, headers=_bearer(TOKEN_A), json={})
            seen[(method, path)] = answer.status_code
    web = {("POST", SEARCH), ("POST", FETCH)}
    assert web <= set(seen)
    assert len(seen) > 20  # the whole surface, not a handful
    assert {call: code for call, code in seen.items() if call not in web and code != 403} == {}
    # With a body the web routes accept, they answer; `{}` is a 422, not a 403.
    assert {seen[call] for call in web} == {422}


@pytest.mark.parametrize(
    "path", [f"/api/v1/projects/{PID}/live", "/api/v1/lanes/live?path=/tmp/x.jsonl"]
)
def test_a_session_token_never_opens_a_live_feed(tmp_path: Path, path: str) -> None:
    hub = _hub(tmp_path)
    hub.mint(RUN_A)
    client = TestClient(hub.app, base_url=f"http://{HOST}")
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(path, headers=_bearer(TOKEN_A)) as socket,
    ):
        socket.receive_json()
    assert closed.value.code == POLICY_VIOLATION


async def test_the_host_and_the_agent_tokens_are_never_read_as_a_session(tmp_path: Path) -> None:
    """Asked last, the session authenticator never shadows the host or the agent; their
    principals keep their own names and budgets."""
    hub = _hub(tmp_path)
    hub.mint(RUN_A)
    async with hub.client() as client:
        await client.post(SEARCH, headers=_bearer(AGENT_TOKEN), json={"query": "q"})
        await client.post(SEARCH, headers=_bearer(HOST_TOKEN), json={"query": "q"})
        await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
    assert [p["principal"] for _, p in hub.audit.records] == ["agent", "host", f"session:{RUN_A}"]


# -- when a token stops working ------------------------------------------------------------------


async def test_an_expired_session_token_is_a_401_and_a_late_call_spends_nothing(
    tmp_path: Path,
) -> None:
    """At the expiry instant the token is refused before any route runs. That late call spent
    neither the session's cap nor the agent's hourly bucket: with both set to one, the same
    session -- seen again a moment before its expiry -- still has its one search."""
    hub = _hub(tmp_path, WebToolSettings(session_searches=1, searches_per_hour=1))
    grant = hub.mint(RUN_A)
    hub.clock.now = grant.expires_at
    async with hub.client() as client:
        late = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
        late_fetch = await client.post(
            FETCH, headers=_bearer(TOKEN_A), json={"url": "https://docs.example/"}
        )
        assert (late.status_code, late_fetch.status_code) == (401, 401)
        assert hub.search.asked == [] and hub.fetch.asked == [] and hub.audit.records == []
        hub.clock.now = grant.expires_at - 0.001
        first = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
        second = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
    assert first.status_code == 200
    assert second.status_code == 429
    assert hub.search.asked == ["q"]


async def test_a_revoked_session_token_is_a_401_and_a_late_call_spends_nothing(
    tmp_path: Path,
) -> None:
    """Revoked mid-run, the token is refused from the next request; the agent's bucket of one
    is still whole afterwards."""
    hub = _hub(tmp_path, WebToolSettings(searches_per_hour=1))
    grant = hub.mint(RUN_A)
    hub.principals.revoke(grant)
    async with hub.client() as client:
        late = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
        agent = await client.post(SEARCH, headers=_bearer(AGENT_TOKEN), json={"query": "q"})
    assert late.status_code == 401
    assert agent.status_code == 200
    assert [p["principal"] for _, p in hub.audit.records] == ["agent"]


async def test_an_unknown_token_is_a_401(tmp_path: Path) -> None:
    hub = _hub(tmp_path)
    async with hub.client() as client:
        refused = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "q"})
    assert refused.status_code == 401


# -- two checks, one spend (R2) ------------------------------------------------------------------


async def test_two_sessions_have_caps_of_their_own(tmp_path: Path) -> None:
    hub = _hub(tmp_path, WebToolSettings(session_searches=1, searches_per_hour=10))
    hub.mint(RUN_A)
    hub.mint(RUN_B)
    async with hub.client() as client:
        a_first = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "a1"})
        a_second = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "a2"})
        b_first = await client.post(SEARCH, headers=_bearer(TOKEN_B), json={"query": "b1"})
    assert (a_first.status_code, a_second.status_code, b_first.status_code) == (200, 429, 200)
    detail = a_second.json()["detail"]
    assert f"session:{RUN_A}" in detail and "[web] session_searches = 1" in detail
    assert hub.search.asked == ["a1", "b1"]


async def test_each_session_call_charges_the_agents_hourly_bucket_exactly_once(
    tmp_path: Path,
) -> None:
    """With the agent's bucket at two: one session search and one agent search spend it, so a
    second agent search is refused -- one charge per session call, neither none nor two -- and
    a session is then refused too, with the agent's budget named."""
    hub = _hub(tmp_path, WebToolSettings(searches_per_hour=2, session_searches=10))
    hub.mint(RUN_A)
    async with hub.client() as client:
        session = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "s"})
        agent = await client.post(SEARCH, headers=_bearer(AGENT_TOKEN), json={"query": "a"})
        agent_again = await client.post(SEARCH, headers=_bearer(AGENT_TOKEN), json={"query": "a"})
        session_again = await client.post(SEARCH, headers=_bearer(TOKEN_A), json={"query": "s"})
    assert (session.status_code, agent.status_code) == (200, 200)
    assert (agent_again.status_code, session_again.status_code) == (429, 429)
    assert "agent has used [web] searches_per_hour = 2" in session_again.json()["detail"]
    assert hub.search.asked == ["s", "a"]
