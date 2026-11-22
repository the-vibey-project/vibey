# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub `vibey acp` talks to in the ACP conformance test: the real one, over memory (Task 10).

`vibey acp` reaches the hub through `HubGateway`, as the scoped agent principal: it reads the
user's `[hub] state_dir`, presents `<state_dir>/agent.token` and finds the hub in
`<state_dir>/serving.json`. This stub writes both files with the real `LocalTokenStore` and
listens on 127.0.0.1 only, so the agent finds it exactly as it finds a hub `vibey serve` runs.

Behind a small stdlib front, every request is answered by **the hub's own FastAPI app**
(`HubAppFactory.build`): its routes, request models, error mapping, Host check, rate limit and
the real `AgentTokenAuthenticator` with the default agent scopes. The app is built over the
real `HubService` (so the chat parse and render, the gate dicts, the spend refusal of a gate
answer and the documents are the hub's: `CliHubDocuments`), and the real `AcpSessionService`
(ownership, folder and seq rules, the list cursor). Only the stores are memory: the repository
ports those services call, given here as the few methods they use, over product records
(`ProjectRecord`, `HumanGateRecord`, `LedgerEvent`). A hub contract change in any document the
agent reads therefore reaches this test. What is still written here, and says so: a project's
status document (`probes.status`; the agent only shows it as code), and the in-memory stores'
own semantics (each mirrors its port's docstring; the Postgres stores have their own tests).

The front holds a chat turn when a test asks (at most `HOLD_SECONDS`, below the gateway's 15 s
timeout), refuses one folder's sessions with a synthetic 400 when a test asks (the real hub has
no such refusal; it stands for any permanent 4xx), records every request and every answer the
agent sent, and counts requests without the agent token. It never drops a connection: a
transport error is what makes the agent run `vibey hub start`, which this test must never do.

Declared by `interfaces/acp_stub_hub_interface.py`.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Final
from urllib.parse import urlsplit
from uuid import UUID

from fastapi.testclient import TestClient

from vibey.application.acp.acp_session_service import AcpSessionService
from vibey.application.acp.dto import SessionEvent, SessionRecord, SessionSummary
from vibey.application.dto import GateAnswerOutcome, HumanGateRecord, ProjectRecord
from vibey.application.hub.hub_service import HubService
from vibey.cli.serve import CliHubDocuments
from vibey.domain.acp.session_log import AcpSessionLimitReached, SessionEventConflict
from vibey.domain.errors import GateAlreadyAnswered, UnknownGate
from vibey.domain.hub_binding import HUB_BINDING
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HUB_SCOPES
from vibey.domain.ledger import LedgerEvent
from vibey.infrastructure.hub.app import HubAppFactory
from vibey.infrastructure.hub.authenticator import AgentTokenAuthenticator
from vibey.infrastructure.hub.live import LedgerAnnouncements
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

HOLD_SECONDS: Final = 10.0
"""The longest a held chat turn waits: below `HubGateway`'s 15 s, so the agent never sees a
timeout (an `httpx` error, which would make it try `vibey hub start`)."""
WAIT_STEP_SECONDS: Final = 0.05
"""How often the server thread checks whether it was asked to stop."""
CHAT: Final = "/api/v1/chat/messages"
SESSIONS: Final = "/api/v1/acp/sessions"
_ANSWER: Final = re.compile(r"^/api/v1/gates/([0-9a-f-]{36})/answer$")
_UNUSED: Final = SimpleNamespace()
"""A port `HubService` never calls on the routes the agent reaches: any use is a 500."""


class StubHub:
    """Declared by `interfaces/acp_stub_hub_interface.py::StubHubInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._store = LocalTokenStore(state_dir)
        self._token = ""
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._client: TestClient | None = None
        self._changed = threading.Condition()
        self._projects: dict[UUID, ProjectRecord] = {}
        self._gates: dict[UUID, HumanGateRecord] = {}
        self._ledger: dict[UUID, list[LedgerEvent]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._answers: list[tuple[str, Mapping[str, Any], str | None]] = []
        self._requests: list[tuple[str, str]] = []
        self._unauthorised = 0
        self._refused: set[str] = set()
        self._holding = False
        self._held = threading.Event()
        self._release = threading.Event()

    # -- lifecycle -----------------------------------------------------------------------

    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("the stub hub is not started")
        return int(self._server.server_address[1])

    def start(self) -> None:
        hub = self

        class _Front(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - the name http.server dispatches to
                hub._serve(self, "GET")

            def do_POST(self) -> None:  # noqa: N802 - the name http.server dispatches to
                hub._serve(self, "POST")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return None  # the agent's stderr is under test; the stub's own stays quiet

        self._token = self._store.agent_token()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Front)
        self._server.daemon_threads = True
        app = HubAppFactory().build(
            self._service(),
            authenticator=AgentTokenAuthenticator(self._token, AGENT_DEFAULT_SCOPES),
            allowed_hosts=HUB_BINDING.allowed_hosts(self.port, frozenset()),
            ready=self._ready,
            live=LedgerAnnouncements(self._no_listen),
            acp_sessions=AcpSessionService(self._session_store(), HUB_SCOPES),
        )
        self._client = TestClient(
            app, base_url=f"http://127.0.0.1:{self.port}", raise_server_exceptions=False
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": WAIT_STEP_SECONDS},
            name="acp-stub-hub",
            daemon=True,
        )
        self._thread.start()
        self._store.record_serving(ServingRecord(host="127.0.0.1", port=self.port, pid=os.getpid()))

    def stop(self) -> None:
        self.release_chat()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=HOLD_SECONDS)

    # -- scripting -----------------------------------------------------------------------

    def set_projects(self, projects: Sequence[ProjectRecord]) -> None:
        with self._changed:
            self._projects = {project.project_id: project for project in projects}

    def append_ledger(self, event: LedgerEvent) -> None:
        with self._changed:
            events = self._ledger.setdefault(event.project_id, [])
            if event.seq != len(events) + 1:
                raise ValueError(f"the next seq of {event.project_id} is {len(events) + 1}")
            events.append(event)

    def set_gates(self, gates: Sequence[HumanGateRecord]) -> None:
        with self._changed:
            self._gates = {gate.gate_id: gate for gate in gates}

    def hold_chat(self) -> None:
        self._held.clear()
        self._release.clear()
        self._holding = True

    def release_chat(self) -> None:
        self._holding = False
        self._release.set()

    def wait_chat_held(self, timeout: float) -> bool:
        return self._held.wait(timeout)

    def refuse_sessions_under(self, cwd: str) -> None:
        with self._changed:
            self._refused.add(cwd)

    def forge_session_event(self, session_id: str, kind: str, payload: Mapping[str, Any]) -> int:
        with self._changed:
            seq = max(self._sessions[session_id]["log"], default=0) + 1
        # Through the hub's own route, as any holder of the agent's key could write it.
        response = self._app().post(
            f"{SESSIONS}/{session_id}/events",
            json={"seq": seq, "kind": kind, "payload": dict(payload)},
            headers={"authorization": f"Bearer {self._token}"},
        )
        if response.status_code != 200:
            raise AssertionError(f"the hub refused the forged event: {response.text}")
        return seq

    def session_events(self, session_id: str) -> tuple[tuple[int, str, Mapping[str, Any]], ...]:
        with self._changed:
            kept = self._sessions.get(session_id)
            log = kept["log"] if kept is not None else {}
            return tuple((seq, *log[seq]) for seq in sorted(log))

    def wait_for_session_event(self, session_id: str, kind: str, timeout: float) -> bool:
        def kept() -> bool:
            session = self._sessions.get(session_id)
            return session is not None and any(k == kind for k, _ in session["log"].values())

        with self._changed:
            return self._changed.wait_for(kept, timeout)

    @property
    def answers(self) -> tuple[tuple[str, Mapping[str, Any], str | None], ...]:
        with self._changed:
            return tuple(self._answers)

    @property
    def requests(self) -> tuple[tuple[str, str], ...]:
        with self._changed:
            return tuple(self._requests)

    @property
    def unauthorised(self) -> int:
        with self._changed:
            return self._unauthorised

    # -- the front -----------------------------------------------------------------------

    def _serve(self, request: BaseHTTPRequestHandler, method: str) -> None:
        path = urlsplit(request.path).path
        authorization = request.headers.get("authorization") or ""
        length = int(request.headers.get("content-length") or 0)
        raw = request.rfile.read(length) if length else b""
        with self._changed:
            self._requests.append((method, path))
            if authorization != f"Bearer {self._token}":
                self._unauthorised += 1
        body = json.loads(raw) if raw else {}
        if method == "POST" and path == CHAT and self._holding:
            self._held.set()
            self._release.wait(HOLD_SECONDS)
        if method == "POST" and (answer := _ANSWER.match(path)):
            given, request_id = body.get("answer"), body.get("request_id")
            with self._changed:
                self._answers.append(
                    (
                        answer.group(1),
                        dict(given) if isinstance(given, Mapping) else {},
                        request_id if isinstance(request_id, str) else None,
                    )
                )
        if method == "POST" and path == SESSIONS and body.get("cwd") in self._refused:
            # Synthetic: the real hub refuses no folder; this stands for any permanent 4xx.
            self._reply(request, 400, b'{"detail": "this stub refuses that folder"}')
            return
        headers = {"authorization": authorization}
        if raw:
            headers["content-type"] = "application/json"
        response = self._app().request(method, request.path, content=raw or None, headers=headers)
        self._reply(request, response.status_code, response.content)

    def _app(self) -> TestClient:
        if self._client is None:
            raise RuntimeError("the stub hub is not started")
        return self._client

    @staticmethod
    def _reply(request: BaseHTTPRequestHandler, status: int, data: bytes) -> None:
        request.send_response(status)
        request.send_header("content-type", "application/json")
        request.send_header("content-length", str(len(data)))
        request.end_headers()
        request.wfile.write(data)

    # -- the hub's stores, in memory -----------------------------------------------------

    def _service(self) -> HubService:
        return HubService(
            projects=SimpleNamespace(get=self._project, list_all=self._all_projects),
            gates=SimpleNamespace(open_all=self._open_gates, open_for_project=self._open_for),
            gate_lookup=SimpleNamespace(get=self._gate),
            gate_answers=SimpleNamespace(answer=self._answer),
            budgets=_UNUSED,
            queue=_UNUSED,
            ledger=_UNUSED,
            ledger_range=SimpleNamespace(range=self._range),
            documents=CliHubDocuments(),
            probes=SimpleNamespace(status=self._status),
            lifecycle=_UNUSED,
        )

    def _session_store(self) -> Any:
        return SimpleNamespace(
            create=self._create,
            append=self._append,
            events_after=self._events_after,
            list=self._list,
            owner=self._owner,
            summary=self._summary,
        )

    @staticmethod
    async def _ready() -> bool:
        return True

    @staticmethod
    async def _no_listen() -> Any:
        raise ConnectionRefusedError("the stub hub has no database to LISTEN on")

    async def _project(self, project_id: UUID) -> ProjectRecord | None:
        with self._changed:
            return self._projects.get(project_id)

    async def _all_projects(self) -> tuple[ProjectRecord, ...]:
        with self._changed:
            return tuple(self._projects.values())

    async def _open_gates(self) -> tuple[HumanGateRecord, ...]:
        with self._changed:
            return tuple(gate for gate in self._gates.values() if gate.answered_at is None)

    async def _open_for(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        return tuple(gate for gate in await self._open_gates() if gate.project_id == project_id)

    async def _gate(self, gate_id: UUID) -> HumanGateRecord | None:
        with self._changed:
            return self._gates.get(gate_id)

    async def _answer(
        self,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        by: str | None = None,
        request_id: str | None = None,
    ) -> GateAnswerOutcome:
        with self._changed:
            gate = self._gates.get(gate_id)
            if gate is None:
                raise UnknownGate(f"no gate {gate_id}")
            if gate.answered_at is not None:
                if request_id is not None and request_id == gate.answer_request_id:
                    return GateAnswerOutcome(gate, replayed=True)
                raise GateAlreadyAnswered(f"gate {gate_id} is already answered")
            answered = replace(
                gate,
                answer=dict(answer),
                answered_at=datetime.now(UTC),
                answered_by=by,
                answer_request_id=request_id,
            )
            self._gates[gate_id] = answered
            return GateAnswerOutcome(answered)

    async def _range(
        self, project_id: UUID, *, from_seq: int, to_seq: int
    ) -> tuple[LedgerEvent, ...]:
        with self._changed:
            events = self._ledger.get(project_id, [])
            return tuple(event for event in events if from_seq <= event.seq <= to_seq)

    async def _status(self, project_id: UUID) -> Any:
        # Hand-written: the agent shows a status document only as a code block.
        project = await self._project(project_id)
        name = project.name if project is not None else "?"
        return {"project": {"name": name, "phase": "BUILD", "cycle": 1}}

    # -- the ACP session store, in memory (AcpSessionRepositoryInterface) ----------------

    async def _create(self, session_id: str, cwd: str, created_by: str, *, limit: int) -> bool:
        with self._changed:
            held = sum(1 for s in self._sessions.values() if s["owner"] == created_by)
            if session_id in self._sessions or held >= limit:
                return False
            self._sessions[session_id] = {
                "owner": created_by,
                "cwd": cwd,
                "log": {},
                "updated_at": datetime.now(UTC),
            }
            self._changed.notify_all()
            return True

    async def _append(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any], *, limit: int
    ) -> bool:
        with self._changed:
            session = self._sessions[session_id]
            log: dict[int, tuple[str, dict[str, Any]]] = session["log"]
            if seq in log:
                if log[seq] != (kind, dict(payload)):
                    raise SessionEventConflict(f"seq {seq} of {session_id} is taken")
                return True
            if len(log) >= limit:
                raise AcpSessionLimitReached(f"session {session_id} is full")
            log[seq] = (kind, dict(payload))
            session["updated_at"] = datetime.now(UTC)
            self._changed.notify_all()
            return True

    async def _events_after(
        self, session_id: str, after: int, limit: int
    ) -> tuple[SessionEvent, ...]:
        with self._changed:
            log = self._sessions[session_id]["log"]
            seqs = [seq for seq in sorted(log) if seq > after][:limit]
            return tuple(SessionEvent(seq, log[seq][0], log[seq][1]) for seq in seqs)

    async def _list(
        self,
        created_by: str,
        *,
        cwd: str | None,
        cursor: tuple[datetime, str] | None,
        limit: int,
    ) -> tuple[SessionRecord, ...]:
        with self._changed:
            found = sorted(
                (
                    (session["updated_at"], session_id, session)
                    for session_id, session in self._sessions.items()
                    if session["owner"] == created_by and cwd in (None, session["cwd"])
                ),
                key=lambda item: (item[0], item[1]),
                reverse=True,
            )
            if cursor is not None:
                found = [item for item in found if (item[0], item[1]) < cursor]
            return tuple(self._record(sid, session) for _, sid, session in found[:limit])

    async def _owner(self, session_id: str) -> tuple[str, str] | None:
        with self._changed:
            session = self._sessions.get(session_id)
            return (session["owner"], session["cwd"]) if session is not None else None

    async def _summary(self, session_id: str) -> SessionSummary:
        with self._changed:
            log = self._sessions[session_id]["log"]
            newest = {kind: payload for _, (kind, payload) in sorted(log.items())}
            return SessionSummary(
                newest_seq=max(log, default=0),
                mode=newest.get("mode"),
                attach=newest.get("attach"),
                title=newest.get("title"),
            )

    @staticmethod
    def _record(session_id: str, session: Mapping[str, Any]) -> SessionRecord:
        log = session["log"]
        titles = [p.get("title") for _, (kind, p) in sorted(log.items()) if kind == "title"]
        newest_kind = log[max(log)][0] if log else None
        return SessionRecord(
            session_id=session_id,
            cwd=session["cwd"],
            title=titles[-1] if titles and isinstance(titles[-1], str) else None,
            updated_at=session["updated_at"],
            closed=newest_kind == "closed",
        )
