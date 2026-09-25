# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's live feed: NOTIFY on append, a WebSocket that resumes after a seq, lanes by
byte offset.

The WebSocket tests drive the app with Starlette's test client and a fake service whose
pages say what they were asked for, so they are about the socket alone: who may open
one (Host, Origin, principal), that a revoked principal is cut off at the next page,
that a feed behind by a full page keeps paging, and that a quiet feed says it is there.
The announcements are tested against real Postgres through migration 0019.
"""

import asyncio
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import HubPrincipal
from vibey.bootstrap import build_app, database_url, migrations_dir
from vibey.domain.errors import UnknownLane, UnknownProject
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.hub import app as app_module
from vibey.infrastructure.hub.app import LIVE_PAGE, POLICY_VIOLATION, HubAppFactory
from vibey.infrastructure.hub.authenticator import HubRequest
from vibey.infrastructure.hub.interfaces.live_interface import LedgerAnnouncementsInterface
from vibey.infrastructure.hub.lanes import LaneEngine, LaneScanner
from vibey.infrastructure.hub.live import LedgerAnnouncements

PID = UUID("11111111-1111-4111-8111-111111111111")
HOST = "127.0.0.1:8765"
OK = {"authorization": "Bearer ok", "host": HOST}


class Toggle:
    """Admits `Bearer ok` until revoked."""

    def __init__(self) -> None:
        self.revoked = False
        self.asked = 0

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        self.asked += 1
        if self.revoked or request.headers.get("authorization") != "Bearer ok":
            return None
        return HubPrincipal(name="host")


class Pages:
    """`ledger_after` returns `pages` in turn, then empty pages; lane tails likewise."""

    def __init__(self, pages: list[Any], raises: Exception | None = None) -> None:
        self.pages = pages
        self.raises = raises
        self.asked: list[int] = []

    async def ledger_after(
        self, principal: Any, project_id: UUID, *, after: int, limit: int
    ) -> Any:
        self.asked.append(after)
        if self.raises is not None:
            raise self.raises
        return self.pages.pop(0) if self.pages else {"events": [], "last_seq": None}

    def lane_tail(self, principal: Any, events_path: str, after: int) -> Any:
        self.asked.append(after)
        if self.raises is not None:
            raise self.raises
        return self.pages.pop(0) if self.pages else {"offset": after, "lines": []}


class Wakes:
    """Hands out a queue that is woken once, immediately."""

    @contextmanager
    def subscribe(self, project_id: UUID) -> Iterator[asyncio.Queue[int]]:
        queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
        queue.put_nowait(1)
        yield queue

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


def _app(service: Pages, auth: Toggle) -> FastAPI:
    async def ready() -> bool:
        return True

    return HubAppFactory().build(
        service,  # type: ignore[arg-type]
        authenticator=auth,
        allowed_hosts=HUB_BINDING.allowed_hosts(8765, frozenset()),
        ready=ready,
        live=Wakes(),
    )


def _page(first: int, count: int) -> dict[str, Any]:
    return {
        "events": [{"seq": n} for n in range(first, first + count)],
        "last_seq": first + count - 1,
    }


def test_the_listener_meets_its_declared_seam() -> None:
    assert isinstance(LedgerAnnouncements(lambda: asyncio.sleep(0)), LedgerAnnouncementsInterface)


@pytest.mark.parametrize(
    "headers",
    [
        {"host": HOST},  # proves nothing
        {**OK, "host": "attacker.example:8765"},  # DNS rebinding
        {**OK, "origin": "https://attacker.example"},  # cross-site WebSocket hijacking
    ],
)
def test_a_socket_that_is_not_admitted_is_closed_before_it_opens(headers: dict[str, str]) -> None:
    client = TestClient(_app(Pages([]), Toggle()), base_url=f"http://{HOST}")
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(f"/api/v1/projects/{PID}/live", headers=headers) as socket,
    ):
        socket.receive_json()
    assert closed.value.code == POLICY_VIOLATION


def test_a_feed_pages_until_caught_up_then_waits_and_heartbeats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "HEARTBEAT_SECONDS", 0.01)
    service = Pages([_page(6, LIVE_PAGE), _page(6 + LIVE_PAGE, 2)])
    client = TestClient(_app(service, Toggle()), base_url=f"http://{HOST}")
    headers = {**OK, "origin": f"http://{HOST}"}
    with client.websocket_connect(
        f"/api/v1/projects/{PID}/live?after=5", headers=headers
    ) as socket:
        first, second = socket.receive_json(), socket.receive_json()
        heartbeat = socket.receive_json()
    assert len(first["events"]) == LIVE_PAGE and len(second["events"]) == 2
    assert heartbeat == {"heartbeat": 5 + LIVE_PAGE + 2}
    # Resumed from positions only: 5, then the last seq of each page.
    assert service.asked[:3] == [5, 5 + LIVE_PAGE, 5 + LIVE_PAGE + 2]


def test_a_principal_revoked_mid_feed_is_cut_off_at_the_next_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "HEARTBEAT_SECONDS", 0.01)
    auth = Toggle()
    service = Pages([_page(1, 1)])
    client = TestClient(_app(service, auth), base_url=f"http://{HOST}")
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(f"/api/v1/projects/{PID}/live", headers=OK) as socket,
    ):
        socket.receive_json()
        auth.revoked = True
        for _ in range(100):  # heartbeats already in flight, then the close
            socket.receive_json()
    assert closed.value.code == POLICY_VIOLATION


def test_a_project_that_does_not_exist_closes_the_feed() -> None:
    client = TestClient(
        _app(Pages([], raises=UnknownProject("x")), Toggle()), base_url=f"http://{HOST}"
    )
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(f"/api/v1/projects/{PID}/live", headers=OK) as socket,
    ):
        socket.receive_json()
    assert closed.value.code == POLICY_VIOLATION


def test_a_lane_feed_sends_new_lines_by_offset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_module, "LANE_POLL_SECONDS", 0.0)
    service = Pages(
        [
            {"offset": 10, "lines": ["a"]},
            {"offset": 10, "lines": []},
            {"offset": 14, "lines": ["b"]},
        ]
    )
    client = TestClient(_app(service, Toggle()), base_url=f"http://{HOST}")
    with client.websocket_connect("/api/v1/lanes/live?path=/x&after=0", headers=OK) as socket:
        assert socket.receive_json()["lines"] == ["a"]
        assert socket.receive_json()["lines"] == ["b"]
    assert service.asked[:3] == [0, 10, 10]


def test_a_lane_feed_is_refused_for_an_unknown_lane_a_revoked_or_unadmitted_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "LANE_POLL_SECONDS", 0.0)
    client = TestClient(
        _app(Pages([], raises=UnknownLane("x")), Toggle()), base_url=f"http://{HOST}"
    )
    with (
        pytest.raises(WebSocketDisconnect) as unknown,
        client.websocket_connect("/api/v1/lanes/live?path=/x", headers=OK) as socket,
    ):
        socket.receive_json()
    assert unknown.value.code == POLICY_VIOLATION
    with (
        pytest.raises(WebSocketDisconnect) as anonymous,
        client.websocket_connect("/api/v1/lanes/live?path=/x", headers={"host": HOST}) as socket,
    ):
        socket.receive_json()
    assert anonymous.value.code == POLICY_VIOLATION
    auth = Toggle()
    live = TestClient(_app(Pages([{"offset": 1, "lines": ["a"]}]), auth), base_url=f"http://{HOST}")
    with (
        pytest.raises(WebSocketDisconnect) as revoked,
        live.websocket_connect("/api/v1/lanes/live?path=/x", headers=OK) as socket,
    ):
        socket.receive_json()
        auth.revoked = True
        socket.receive_json()
    assert revoked.value.code == POLICY_VIOLATION


# --- lanes by byte offset ---------------------------------------------------------------


def _scanner(tmp_path: Path) -> tuple[LaneScanner, Path]:
    events = tmp_path / ".qwenloop" / "runs" / "r1" / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_bytes(b'{"n": 1}\n{"n": 2}\n{"n": 3')
    scanner = LaneScanner(
        engines=[LaneEngine("qwenloop", ".qwenloop")], roots=[tmp_path], now=lambda: 0.0
    )
    return scanner, events


def test_a_tail_returns_whole_lines_and_the_offset_to_resume_from(tmp_path: Path) -> None:
    scanner, events = _scanner(tmp_path)
    first = scanner.tail(str(events), 0)
    assert first["lines"] == ['{"n": 1}', '{"n": 2}'] and first["offset"] == 18
    assert scanner.tail(str(events), 18)["lines"] == []
    with events.open("ab") as handle:
        handle.write(b"}\n")
    assert scanner.tail(str(events), 18) == {
        "events_path": str(events),
        "from": 18,
        "offset": 27,
        "lines": ['{"n": 3}'],
    }
    assert scanner.tail(str(events), 999)["from"] == 0
    assert scanner.tail(str(events), 0, max_bytes=10)["lines"] == ['{"n": 1}']


def test_only_a_listed_lane_is_ever_read(tmp_path: Path) -> None:
    scanner, _ = _scanner(tmp_path)
    (tmp_path / "secret").write_text("no\n")
    for path in (str(tmp_path / "secret"), "/etc/passwd", "../../events.jsonl"):
        with pytest.raises(UnknownLane):
            scanner.tail(path, 0)


# --- NOTIFY through migration 0019, against real Postgres ---------------------------------


@pytest.fixture
async def _an_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    conn = await asyncpg.connect(owner)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()
    await TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir())
    monkeypatch.setenv("VIBEY_PG_URL", os.environ["VIBEY_TEST_APP_DATABASE_URL"])


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_an_append_wakes_its_projects_feeds_and_no_others(tmp_path: Path) -> None:
    announcements = LedgerAnnouncements(lambda: asyncpg.connect(database_url()))
    await announcements.stop()  # nothing to stop yet
    await announcements.start()
    try:
        async with build_app() as resources:
            project = await resources.projects.create("live", tmp_path, max_cycles=1, config={})
            other = uuid4()
            with (
                announcements.subscribe(project.project_id) as mine,
                announcements.subscribe(other) as theirs,
                announcements.subscribe(project.project_id) as twin,
            ):
                event = await resources.ledger.append(
                    LedgerEventDraft(
                        project_id=project.project_id,
                        cycle=1,
                        phase=Phase.BUILD,
                        kind=EventKind.TURN_COMPLETED,
                        engine_id=None,
                        job_id=None,
                        causation_id=None,
                        correlation_id=uuid4(),
                        provenance=Provenance.TRUSTED,
                        produced_at=datetime.now(UTC),
                        payload={"n": 1},
                        digest="",
                    )
                )
                assert await asyncio.wait_for(mine.get(), 5) == event.seq
                assert await asyncio.wait_for(twin.get(), 5) == event.seq
                assert theirs.empty()
                # A second append while a wake-up is pending is folded into it.
                mine.put_nowait(0)
                announcements._heard(
                    None, 0, "", json.dumps({"project_id": str(project.project_id), "seq": 9})
                )
                assert mine.qsize() == 1
                # Anything that is not an announcement is ignored.
                announcements._heard(None, 0, "", "not json")
                announcements._heard(None, 0, "", json.dumps({"seq": 1}))
    finally:
        await announcements.stop()
    assert announcements._subscribers == {}


class Gone:
    """A socket whose client has already left: the first send says so."""

    class _State:
        name = "CONNECTING"

    class _Url:
        path = "/"
        query = ""

    headers = OK
    url = _Url()

    def __init__(self) -> None:
        self.client_state = self._State()
        self.closed: int | None = None

    async def accept(self) -> None:
        self.client_state.name = "CONNECTED"

    async def send_json(self, data: Any) -> None:
        raise WebSocketDisconnect(1001)

    async def close(self, code: int) -> None:  # pragma: no cover - never reached here
        self.closed = code


async def test_a_client_that_leaves_ends_its_feeds() -> None:
    app = _app(Pages([_page(1, 1), {"offset": 1, "lines": ["a"]}]), Toggle())
    endpoints = {
        getattr(route, "path", ""): getattr(route, "endpoint", None) for route in app.routes
    }
    feed, lane = Gone(), Gone()
    await endpoints["/api/v1/projects/{project_id}/live"](feed, PID, 0)
    await endpoints["/api/v1/lanes/live"](lane, "/x", 0)
    assert feed.closed is None and lane.closed is None
